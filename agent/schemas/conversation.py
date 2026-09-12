from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from .planning import GeminiContractModel


class ConversationTurnRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ConversationHistoryTurn(GeminiContractModel):
    """A size-bounded history projection; never a raw database model."""

    sequence: int = Field(ge=1)
    role: ConversationTurnRole
    message: str = Field(min_length=1, max_length=500)


class FollowUpCandidate(GeminiContractModel):
    """One server-derived prior exchange the resolver may reference."""

    turn_sequence: int = Field(ge=1)
    user_message: str = Field(min_length=1, max_length=500)
    assistant_message: str | None = Field(default=None, max_length=500)


class FollowUpMode(StrEnum):
    STANDALONE = "standalone"
    RESOLVED = "resolved"
    CLARIFICATION = "clarification"


class FollowUpResolution(GeminiContractModel):
    """Non-executable reference resolution produced before planning."""

    mode: FollowUpMode
    referenced_turn_sequences: list[int] = Field(default_factory=list, max_length=2)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if len(self.referenced_turn_sequences) != len(set(self.referenced_turn_sequences)):
            raise ValueError("referenced turns must not contain duplicates")
        if self.mode == FollowUpMode.STANDALONE and self.referenced_turn_sequences:
            raise ValueError("standalone questions cannot reference prior turns")
        if self.mode == FollowUpMode.RESOLVED and len(self.referenced_turn_sequences) != 1:
            raise ValueError("resolved follow-ups require exactly one prior turn")
        if self.mode == FollowUpMode.CLARIFICATION and not self.referenced_turn_sequences:
            raise ValueError("clarification requires ambiguous candidate turns")
        return self
