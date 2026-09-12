import asyncio
from unittest import IsolatedAsyncioTestCase

from google.adk.tools import FunctionTool

from agent.executors import MultiToolExecutor, build_execution_waves
from agent.schemas import (
    Capability,
    ContextField,
    ContextResolution,
    ExecutionPlan,
    ExecutionStep,
    IntentType,
    QuestionAnalysis,
    ResultStatus,
    StepExecutionState,
)
from agent.tool_registry import ToolBuildContext
from tools.academic import AcademicToolActor


def successful_output(value: str) -> dict:
    return {"status": "success", "data": {"value": value}}


class FakeRegistry:
    def __init__(self, functions):
        self.functions = functions

    def tool_for_capability(self, capability, *, context):
        del context
        function = self.functions.get(capability)
        return FunctionTool(function) if function else None


def parallel_plan() -> ExecutionPlan:
    return ExecutionPlan(
        steps=[
            ExecutionStep(
                step_id="records",
                capability=Capability.ACADEMIC_RECORDS,
                purpose="성적을 조회한다.",
                uses_context=[ContextField.AUTHENTICATED_STUDENT],
            ),
            ExecutionStep(
                step_id="schedule",
                capability=Capability.CURRENT_SCHEDULE,
                purpose="시간표를 조회한다.",
                uses_context=[ContextField.AUTHENTICATED_STUDENT],
            ),
        ],
        rationale="두 조회는 서로 독립적이다.",
    )


def parallel_analysis() -> QuestionAnalysis:
    return QuestionAnalysis(
        intents=[IntentType.PERSONAL_ACADEMIC],
        capabilities=[Capability.ACADEMIC_RECORDS, Capability.CURRENT_SCHEDULE],
        rationale="성적과 시간표가 모두 필요하다.",
    )


class MultiToolExecutorTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.context_resolution = ContextResolution(
            resolved_fields=[ContextField.AUTHENTICATED_STUDENT]
        )
        self.tool_context = ToolBuildContext(
            actor=AcademicToolActor(student_number="MOCK-2026-008")
        )

    def test_dependency_graph_is_grouped_into_parallel_waves(self):
        plan = ExecutionPlan(
            steps=[
                *parallel_plan().steps,
                ExecutionStep(
                    step_id="knowledge",
                    capability=Capability.UNIVERSITY_KNOWLEDGE,
                    purpose="학교 규정을 조회한다.",
                    depends_on=["records", "schedule"],
                ),
            ],
            rationale="두 조회 후 규정을 확인한다.",
        )

        self.assertEqual(
            build_execution_waves(plan),
            [["records", "schedule"], ["knowledge"]],
        )

    async def test_independent_tools_start_concurrently(self):
        started: list[str] = []
        both_started = asyncio.Event()

        async def get_academic_records():
            """Fake academic record lookup."""
            started.append("records")
            if len(started) == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=0.2)
            return successful_output("records")

        async def get_current_schedule():
            """Fake schedule lookup."""
            started.append("schedule")
            if len(started) == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=0.2)
            return successful_output("schedule")

        executor = MultiToolExecutor(
            registry=FakeRegistry(
                {
                    Capability.ACADEMIC_RECORDS: get_academic_records,
                    Capability.CURRENT_SCHEDULE: get_current_schedule,
                }
            ),
            step_timeout_seconds=1,
        )

        result = await executor.execute(
            plan=parallel_plan(),
            analysis=parallel_analysis(),
            context_resolution=self.context_resolution,
            tool_context=self.tool_context,
            question="내 성적과 이번 학기 시간표 알려줘",
        )

        self.assertCountEqual(started, ["records", "schedule"])
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.execution_waves, [["records", "schedule"]])
        self.assertEqual(
            [step.step_id for step in result.steps],
            ["records", "schedule"],
        )

    async def test_dependency_runs_after_predecessor_and_receives_its_result(self):
        calls: list[str] = []

        async def get_student_profile():
            """Fake student profile lookup."""
            calls.append("profile")
            return {
                "status": "success",
                "data": {"primary_major_name": "컴퓨터·AI학부"},
            }

        async def search_university_knowledge(question: str):
            """Fake university knowledge lookup."""
            calls.append(question)
            return successful_output("knowledge")

        async def resolve_arguments(step, question, dependencies):
            if step.capability == Capability.UNIVERSITY_KNOWLEDGE:
                major = dependencies["profile"].output["data"][
                    "primary_major_name"
                ]
                return {"question": f"{question} / 확인된 전공: {major}"}
            return {}

        plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    step_id="profile",
                    capability=Capability.STUDENT_PROFILE,
                    purpose="전공을 확인한다.",
                    uses_context=[ContextField.AUTHENTICATED_STUDENT],
                    produces_context=[ContextField.PRIMARY_MAJOR],
                ),
                ExecutionStep(
                    step_id="knowledge",
                    capability=Capability.UNIVERSITY_KNOWLEDGE,
                    purpose="전공 규정을 조회한다.",
                    depends_on=["profile"],
                    uses_context=[ContextField.PRIMARY_MAJOR],
                ),
            ],
            rationale="확인한 전공으로 규정을 검색한다.",
        )
        analysis = QuestionAnalysis(
            intents=[
                IntentType.PERSONAL_ACADEMIC,
                IntentType.UNIVERSITY_KNOWLEDGE,
            ],
            capabilities=[
                Capability.STUDENT_PROFILE,
                Capability.UNIVERSITY_KNOWLEDGE,
            ],
            rationale="학생 전공과 공식 규정이 필요하다.",
        )
        resolution = ContextResolution(
            resolved_fields=[ContextField.AUTHENTICATED_STUDENT],
            deferred_fields=[ContextField.PRIMARY_MAJOR],
        )
        executor = MultiToolExecutor(
            registry=FakeRegistry(
                {
                    Capability.STUDENT_PROFILE: get_student_profile,
                    Capability.UNIVERSITY_KNOWLEDGE: search_university_knowledge,
                }
            ),
            argument_resolver=resolve_arguments,
        )

        result = await executor.execute(
            plan=plan,
            analysis=analysis,
            context_resolution=resolution,
            tool_context=self.tool_context,
            question="내 전공 졸업학점 알려줘",
        )

        self.assertEqual(calls[0], "profile")
        self.assertIn("컴퓨터·AI학부", calls[1])
        self.assertEqual(result.execution_waves, [["profile"], ["knowledge"]])
        self.assertEqual(result.status, ResultStatus.SUCCESS)

    async def test_timeout_is_reported_without_discarding_other_success(self):
        async def get_academic_records():
            """Fake slow record lookup."""
            await asyncio.sleep(0.1)
            return successful_output("records")

        async def get_current_schedule():
            """Fake schedule lookup."""
            return successful_output("schedule")

        executor = MultiToolExecutor(
            registry=FakeRegistry(
                {
                    Capability.ACADEMIC_RECORDS: get_academic_records,
                    Capability.CURRENT_SCHEDULE: get_current_schedule,
                }
            ),
            step_timeout_seconds=0.01,
        )

        result = await executor.execute(
            plan=parallel_plan(),
            analysis=parallel_analysis(),
            context_resolution=self.context_resolution,
            tool_context=self.tool_context,
            question="내 성적과 시간표 알려줘",
        )

        self.assertEqual(result.status, ResultStatus.PARTIAL)
        self.assertEqual(result.steps[0].state, StepExecutionState.TIMED_OUT)
        self.assertTrue(result.steps[0].error.retryable)
        self.assertEqual(result.steps[1].state, StepExecutionState.SUCCESS)
        self.assertIsNotNone(result.steps[1].output)

    async def test_exception_isolated_as_partial_failure(self):
        async def get_academic_records():
            """Fake broken record lookup."""
            raise RuntimeError("sensitive internal detail")

        async def get_current_schedule():
            """Fake schedule lookup."""
            return successful_output("schedule")

        executor = MultiToolExecutor(
            registry=FakeRegistry(
                {
                    Capability.ACADEMIC_RECORDS: get_academic_records,
                    Capability.CURRENT_SCHEDULE: get_current_schedule,
                }
            )
        )

        result = await executor.execute(
            plan=parallel_plan(),
            analysis=parallel_analysis(),
            context_resolution=self.context_resolution,
            tool_context=self.tool_context,
            question="내 성적과 시간표 알려줘",
        )

        self.assertEqual(result.status, ResultStatus.PARTIAL)
        self.assertEqual(result.steps[0].state, StepExecutionState.ERROR)
        self.assertNotIn("sensitive", result.steps[0].error.message)
        self.assertEqual(result.steps[1].state, StepExecutionState.SUCCESS)

    async def test_failed_dependency_blocks_downstream_tool(self):
        knowledge_called = False

        async def get_student_profile():
            """Fake unavailable profile lookup."""
            return {"status": "unavailable", "data": None}

        async def search_university_knowledge(question: str):
            """Fake knowledge lookup that must not run."""
            nonlocal knowledge_called
            knowledge_called = True
            return successful_output(question)

        plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    step_id="profile",
                    capability=Capability.STUDENT_PROFILE,
                    purpose="전공을 확인한다.",
                    uses_context=[ContextField.AUTHENTICATED_STUDENT],
                    produces_context=[ContextField.PRIMARY_MAJOR],
                ),
                ExecutionStep(
                    step_id="knowledge",
                    capability=Capability.UNIVERSITY_KNOWLEDGE,
                    purpose="전공 규정을 조회한다.",
                    depends_on=["profile"],
                    uses_context=[ContextField.PRIMARY_MAJOR],
                ),
            ],
            rationale="프로필 결과가 있어야 규정을 조회한다.",
        )
        analysis = QuestionAnalysis(
            intents=[
                IntentType.PERSONAL_ACADEMIC,
                IntentType.UNIVERSITY_KNOWLEDGE,
            ],
            capabilities=[
                Capability.STUDENT_PROFILE,
                Capability.UNIVERSITY_KNOWLEDGE,
            ],
            rationale="두 기능이 필요하다.",
        )
        resolution = ContextResolution(
            resolved_fields=[ContextField.AUTHENTICATED_STUDENT],
            deferred_fields=[ContextField.PRIMARY_MAJOR],
        )
        executor = MultiToolExecutor(
            registry=FakeRegistry(
                {
                    Capability.STUDENT_PROFILE: get_student_profile,
                    Capability.UNIVERSITY_KNOWLEDGE: search_university_knowledge,
                }
            )
        )

        result = await executor.execute(
            plan=plan,
            analysis=analysis,
            context_resolution=resolution,
            tool_context=self.tool_context,
            question="내 전공 졸업학점 알려줘",
        )

        self.assertFalse(knowledge_called)
        self.assertEqual(result.status, ResultStatus.UNAVAILABLE)
        self.assertEqual(result.steps[0].state, StepExecutionState.UNAVAILABLE)
        self.assertEqual(result.steps[1].state, StepExecutionState.BLOCKED)
        self.assertEqual(
            result.steps[1].error.code,
            "DEPENDENCY_UNAVAILABLE",
        )

