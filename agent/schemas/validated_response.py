from typing import Self

from pydantic import ConfigDict, Field, model_validator

from .action import ActionReference
from .base import ContractModel
from .response_draft import ResponseDraft
from .source import SourceReference
from .status import ResultStatus


class ValidatedResponse(ContractModel):
    """Server-approved response safe for the API/UI boundary."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    status: ResultStatus
    answer: str = Field(min_length=10, max_length=500)
    sources: list[SourceReference] = Field(default_factory=list)
    actions: list[ActionReference] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list, max_length=3)
    follow_up_question: str | None = Field(default=None, max_length=200)

    @classmethod
    def from_draft(
        cls,
        draft: ResponseDraft,
        *,
        sources: list[SourceReference],
        actions: list[ActionReference],
    ) -> "ValidatedResponse":
        return cls(
            status=draft.status,
            answer=draft.answer,
            sources=sources,
            actions=actions,
            limitations=draft.limitations,
            follow_up_question=draft.follow_up_question,
        )

    @model_validator(mode="after")
    def validate_follow_up_question(self) -> Self:
        if self.status == ResultStatus.CLARIFICATION:
            if not self.follow_up_question:
                raise ValueError("clarification requires a follow_up_question")
        elif self.follow_up_question is not None:
            raise ValueError("follow_up_question is only allowed for clarification")
        return self

