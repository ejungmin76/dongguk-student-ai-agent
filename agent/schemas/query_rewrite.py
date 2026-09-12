from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from .base import ContractModel
from .planning import ContextField, GeminiContractModel


class QueryTarget(StrEnum):
    UNIVERSITY_KNOWLEDGE = "university_knowledge"
    ACADEMIC_RECORDS = "academic_records"
    CURRENT_SCHEDULE = "current_schedule"
    NDRIMS_MENU = "ndrims_menu"


class QueryRewriteProposal(GeminiContractModel):
    """Model selection only: it never contains a rewritten query or a value."""

    target: QueryTarget
    context_fields: list[ContextField] = Field(default_factory=list, max_length=3)
    include_follow_up_reference: bool = False
    rationale: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_fields(self) -> Self:
        if len(self.context_fields) != len(set(self.context_fields)):
            raise ValueError("rewrite context fields must not contain duplicates")
        if ContextField.AUTHENTICATED_STUDENT in self.context_fields:
            raise ValueError("authenticated student must never be added to a query")
        return self


class AppliedQueryContext(ContractModel):
    field: ContextField
    value: str = Field(min_length=1, max_length=200)


class RewrittenQuery(ContractModel):
    """Auditable server-built query passed to a single retrieval/tool boundary."""

    target: QueryTarget
    original_query: str = Field(min_length=1, max_length=2_000)
    rewritten_query: str = Field(min_length=1, max_length=2_500)
    applied_context: list[AppliedQueryContext] = Field(default_factory=list, max_length=3)
    referenced_turn_sequence: int | None = Field(default=None, ge=1)
    unchanged: bool
