from django.test import SimpleTestCase

from agent.fallback import FallbackPolicy, FallbackPolicyError
from agent.responders import build_response_agent_input
from agent.schemas import (
    Capability,
    ContextItem,
    ErrorDetail,
    FallbackMode,
    PlanExecutionResult,
    ResponseContext,
    ResponseDraft,
    ResultStatus,
    StepExecutionState,
    ToolStepExecution,
)


def execution(*steps, status):
    return PlanExecutionResult(
        status=status,
        steps=list(steps),
        execution_waves=[[step.step_id for step in steps]],
        duration_ms=1,
    )


class FallbackPolicyTests(SimpleTestCase):
    def setUp(self):
        self.policy = FallbackPolicy()
        self.partial_context = ResponseContext(
            status=ResultStatus.PARTIAL,
            items=[
                ContextItem(
                    step_id="records",
                    capability=Capability.ACADEMIC_RECORDS,
                    data={"earned_credits": "93"},
                )
            ],
            token_budget=2500,
            estimated_tokens=50,
        )
        self.partial_execution = execution(
            ToolStepExecution(
                step_id="records",
                capability=Capability.ACADEMIC_RECORDS,
                state=StepExecutionState.SUCCESS,
                duration_ms=1,
                output={"status": "success", "data": {"earned_credits": "93"}},
            ),
            ToolStepExecution(
                step_id="knowledge",
                capability=Capability.UNIVERSITY_KNOWLEDGE,
                state=StepExecutionState.TIMED_OUT,
                duration_ms=1,
                error=ErrorDetail(
                    code="TOOL_TIMEOUT",
                    message="internal timeout detail",
                    retryable=True,
                ),
            ),
            status=ResultStatus.PARTIAL,
        )

    def test_partial_keeps_successful_capability_and_forces_safe_limitations(self):
        directive = self.policy.decide(
            context=self.partial_context,
            execution=self.partial_execution,
        )

        self.assertEqual(directive.mode, FallbackMode.RESPONSE_AGENT)
        self.assertEqual(directive.available_capabilities, [Capability.ACADEMIC_RECORDS])
        self.assertEqual(directive.failed_steps[0].capability, Capability.UNIVERSITY_KNOWLEDGE)
        self.assertTrue(directive.failed_steps[0].retryable)
        self.assertNotIn("internal timeout detail", str(directive.model_dump()))
        self.assertEqual(len(directive.required_limitations), 2)

    def test_partial_finalization_merges_server_limitations_before_validation(self):
        directive = self.policy.decide(
            context=self.partial_context,
            execution=self.partial_execution,
        )
        draft = ResponseDraft(
            status=ResultStatus.PARTIAL,
            answer="현재 취득학점은 93학점입니다.",
            limitations=["공식 기준은 이번 응답에서 확인하지 못했습니다."],
        )

        response = self.policy.finalize(
            directive=directive,
            context=self.partial_context,
            draft=draft,
        )

        self.assertEqual(response.status, ResultStatus.PARTIAL)
        self.assertEqual(response.answer, draft.answer)
        self.assertEqual(len(response.limitations), 3)

    def test_unavailable_returns_direct_retry_response(self):
        context = ResponseContext(
            status=ResultStatus.UNAVAILABLE,
            token_budget=2500,
            estimated_tokens=10,
        )
        unavailable_execution = execution(
            ToolStepExecution(
                step_id="knowledge",
                capability=Capability.UNIVERSITY_KNOWLEDGE,
                state=StepExecutionState.UNAVAILABLE,
                duration_ms=1,
                output={"status": "unavailable", "errors": []},
            ),
            status=ResultStatus.UNAVAILABLE,
        )
        directive = self.policy.decide(
            context=context,
            execution=unavailable_execution,
        )

        response = self.policy.finalize(directive=directive, context=context)

        self.assertEqual(directive.mode, FallbackMode.DIRECT_RESPONSE)
        self.assertEqual(response.status, ResultStatus.UNAVAILABLE)
        self.assertIn("확인하지 못했어요", response.answer)

    def test_clarification_uses_server_question_without_calling_response_agent(self):
        context = ResponseContext(
            status=ResultStatus.CLARIFICATION,
            token_budget=2500,
            estimated_tokens=10,
        )
        directive = self.policy.decide(
            context=context,
            clarification_question="어느 학기를 기준으로 확인할까요?",
        )

        response = self.policy.finalize(directive=directive, context=context)

        self.assertEqual(directive.mode, FallbackMode.DIRECT_RESPONSE)
        self.assertEqual(response.follow_up_question, "어느 학기를 기준으로 확인할까요?")
        with self.assertRaises(FallbackPolicyError):
            self.policy.decide(context=context)

    def test_truncated_success_forces_disclosure_before_response_agent(self):
        context = ResponseContext(
            status=ResultStatus.SUCCESS,
            items=[
                ContextItem(
                    step_id="knowledge",
                    capability=Capability.UNIVERSITY_KNOWLEDGE,
                    data={"results": []},
                )
            ],
            token_budget=2500,
            estimated_tokens=100,
            truncated=True,
        )

        directive = self.policy.decide(context=context)
        payload = build_response_agent_input(
            question="졸업 기준 알려줘",
            context=context,
            fallback=directive,
        )

        self.assertEqual(directive.mode, FallbackMode.RESPONSE_AGENT)
        self.assertEqual(len(directive.required_limitations), 1)
        self.assertIn("required_limitations", payload)
        self.assertNotIn("error_code", payload)

