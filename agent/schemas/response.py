from typing import Self

from pydantic import ConfigDict, Field, model_validator

from .base import ContractModel
from .status import ResultStatus


class AgentResponse(ContractModel):
    """Minimal structured response used by the initial ADK agent."""

    # Gemini's response_schema API does not accept JSON Schema's
    # additionalProperties keyword, which Pydantic emits for extra="forbid".
    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    status: ResultStatus
    answer: str = Field(min_length=1)
    follow_up_question: str | None = None

    @model_validator(mode="after")
    def validate_follow_up_question(self) -> Self:
        if self.status == ResultStatus.CLARIFICATION:
            if not self.follow_up_question:
                raise ValueError("clarification responses require a follow-up question")
        elif self.follow_up_question is not None:
            raise ValueError("only clarification responses may include a follow-up question")
        return self
