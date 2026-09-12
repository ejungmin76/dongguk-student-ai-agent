from typing import Self

from pydantic import ConfigDict, Field, model_validator

from .planning import GeminiContractModel
from .status import ResultStatus


class ResponseDraft(GeminiContractModel):
    """Structured Korean answer draft generated only from ResponseContext."""

    status: ResultStatus
    answer: str = Field(min_length=10, max_length=500)
    source_ids: list[str] = Field(default_factory=list, max_length=5)
    action_ids: list[str] = Field(default_factory=list, max_length=5)
    limitations: list[str] = Field(default_factory=list, max_length=3)
    follow_up_question: str | None = Field(default=None, max_length=200)

    # Gemini's response_schema API rejects Pydantic's additionalProperties.
    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @model_validator(mode="after")
    def validate_response_shape(self) -> Self:
        for values, name in (
            (self.source_ids, "source_ids"),
            (self.action_ids, "action_ids"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must not contain duplicates")

        if self.status == ResultStatus.CLARIFICATION:
            if not self.follow_up_question:
                raise ValueError("clarification requires a follow_up_question")
        elif self.follow_up_question is not None:
            raise ValueError("follow_up_question is only allowed for clarification")
        return self

