from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from .base import ContractModel
from .planning import Capability
from .status import ResultStatus
from .tool_execution import StepExecutionState


class FallbackMode(StrEnum):
    RESPONSE_AGENT = "response_agent"
    DIRECT_RESPONSE = "direct_response"


class FailedStepSummary(ContractModel):
    """Safe failure metadata; internal error messages are intentionally omitted."""

    step_id: str
    capability: Capability
    state: StepExecutionState
    error_code: str | None = None
    retryable: bool = False


class FallbackDirective(ContractModel):
    """Server policy controlling how a non-ideal result reaches the student."""

    status: ResultStatus
    mode: FallbackMode
    available_capabilities: list[Capability] = Field(default_factory=list)
    failed_steps: list[FailedStepSummary] = Field(default_factory=list)
    required_limitations: list[str] = Field(default_factory=list, max_length=3)
    direct_answer: str | None = Field(default=None, max_length=500)
    follow_up_question: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.mode == FallbackMode.DIRECT_RESPONSE and not self.direct_answer:
            raise ValueError("direct response fallback requires direct_answer")
        if self.mode == FallbackMode.RESPONSE_AGENT and self.direct_answer is not None:
            raise ValueError("response-agent fallback cannot have direct_answer")
        if self.status == ResultStatus.CLARIFICATION:
            if not self.follow_up_question:
                raise ValueError("clarification fallback requires follow_up_question")
        elif self.follow_up_question is not None:
            raise ValueError("follow_up_question is only allowed for clarification")
        return self

