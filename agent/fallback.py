"""Deterministic fallback policy for partial, unavailable, and clarification states."""

from agent.schemas import (
    FailedStepSummary,
    FallbackDirective,
    FallbackMode,
    PlanExecutionResult,
    ResponseContext,
    ResponseDraft,
    ResultStatus,
    StepExecutionState,
    ValidatedResponse,
)
from agent.validators import ResponseValidator, default_response_validator


class FallbackPolicyError(ValueError):
    pass


class FallbackPolicy:
    """Choose a safe response path without exposing internal failure messages."""

    def decide(
        self,
        *,
        context: ResponseContext,
        execution: PlanExecutionResult | None = None,
        clarification_question: str | None = None,
    ) -> FallbackDirective:
        available, failed_steps, has_retryable_failure = self._execution_summary(execution)

        if context.status == ResultStatus.CLARIFICATION:
            if not clarification_question:
                raise FallbackPolicyError(
                    "clarification response requires a follow-up question"
                )
            return FallbackDirective(
                status=ResultStatus.CLARIFICATION,
                mode=FallbackMode.DIRECT_RESPONSE,
                available_capabilities=available,
                failed_steps=failed_steps,
                direct_answer="정확히 안내하려면 한 가지 정보를 더 확인해야 해요.",
                follow_up_question=clarification_question,
            )

        if context.status == ResultStatus.UNAVAILABLE:
            retry_message = (
                "잠시 후 다시 시도해 주세요."
                if has_retryable_failure
                else "질문을 조금 더 구체적으로 입력하거나 공식 안내를 확인해 주세요."
            )
            return FallbackDirective(
                status=ResultStatus.UNAVAILABLE,
                mode=FallbackMode.DIRECT_RESPONSE,
                available_capabilities=available,
                failed_steps=failed_steps,
                required_limitations=["현재 필요한 정보를 모두 확인하지 못했습니다."],
                direct_answer=f"현재 필요한 정보를 확인하지 못했어요. {retry_message}",
            )

        limitations: list[str] = []
        if context.status == ResultStatus.PARTIAL:
            limitations.append(
                "일부 정보는 현재 확인하지 못해, 확인된 결과만 기준으로 안내합니다."
            )
            if has_retryable_failure:
                limitations.append("일시적인 문제일 수 있으니 잠시 후 다시 시도해 주세요.")
        if context.truncated:
            limitations.append(
                "결과 일부가 길이 제한으로 제외되어, 현재 보이는 정보만 기준으로 안내합니다."
            )

        return FallbackDirective(
            status=context.status,
            mode=FallbackMode.RESPONSE_AGENT,
            available_capabilities=available,
            failed_steps=failed_steps,
            required_limitations=limitations,
        )

    def finalize(
        self,
        *,
        directive: FallbackDirective,
        context: ResponseContext,
        draft: ResponseDraft | None = None,
        validator: ResponseValidator = default_response_validator,
    ) -> ValidatedResponse:
        """Return direct fallbacks or merge required limitations before validation."""

        if directive.mode == FallbackMode.DIRECT_RESPONSE:
            return ValidatedResponse(
                status=directive.status,
                answer=directive.direct_answer or "",
                limitations=directive.required_limitations,
                follow_up_question=directive.follow_up_question,
            )
        if draft is None:
            raise FallbackPolicyError("response-agent fallback requires a response draft")

        merged_limitations = self._deduplicate(
            [*directive.required_limitations, *draft.limitations]
        )
        merged_draft = draft.model_copy(
            update={"limitations": merged_limitations}
        )
        return validator.validate(merged_draft, context=context)

    @staticmethod
    def _execution_summary(
        execution: PlanExecutionResult | None,
    ) -> tuple[list, list[FailedStepSummary], bool]:
        if execution is None:
            return [], [], False

        available = []
        failed_steps: list[FailedStepSummary] = []
        has_retryable_failure = False
        for step in execution.steps:
            if step.is_usable:
                if step.capability not in available:
                    available.append(step.capability)
                continue
            error = step.error
            if error and error.retryable:
                has_retryable_failure = True
            failed_steps.append(
                FailedStepSummary(
                    step_id=step.step_id,
                    capability=step.capability,
                    state=step.state,
                    error_code=error.code if error else None,
                    retryable=error.retryable if error else False,
                )
            )
        return available, failed_steps, has_retryable_failure

    @staticmethod
    def _deduplicate(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))


default_fallback_policy = FallbackPolicy()

