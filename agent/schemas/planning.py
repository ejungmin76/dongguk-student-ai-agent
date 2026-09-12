from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GeminiContractModel(BaseModel):
    """Pydantic contract compatible with Gemini response_schema."""

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class IntentType(StrEnum):
    UNIVERSITY_KNOWLEDGE = "university_knowledge"
    PERSONAL_ACADEMIC = "personal_academic"
    NDRIMS_NAVIGATION = "ndrims_navigation"
    GENERAL_CONVERSATION = "general_conversation"
    UNKNOWN = "unknown"


class Capability(StrEnum):
    STUDENT_PROFILE = "student_profile"
    ACADEMIC_RECORDS = "academic_records"
    CURRENT_SCHEDULE = "current_schedule"
    UNIVERSITY_KNOWLEDGE = "university_knowledge"
    NDRIMS_MENU = "ndrims_menu"
    GENERAL_RESPONSE = "general_response"


class ContextField(StrEnum):
    AUTHENTICATED_STUDENT = "authenticated_student"
    PRIMARY_MAJOR = "primary_major"
    ADMISSION_YEAR = "admission_year"
    CURRENT_TERM = "current_term"
    TARGET_TERM = "target_term"


class ContextSource(StrEnum):
    USER_MESSAGE = "user_message"
    SESSION = "session"
    STUDENT_PROFILE = "student_profile"
    SYSTEM_CLOCK = "system_clock"
    USER_CLARIFICATION = "user_clarification"


class ContextNeed(GeminiContractModel):
    field: ContextField
    source: ContextSource
    reason: str = Field(min_length=1, max_length=200)


class QuestionAnalysis(GeminiContractModel):
    """Meaning-level analysis; it never contains model-generated tool names."""

    intents: list[IntentType] = Field(min_length=1)
    capabilities: list[Capability] = Field(default_factory=list)
    context_needs: list[ContextNeed] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    rationale: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def validate_analysis(self) -> Self:
        if len(self.intents) != len(set(self.intents)):
            raise ValueError("intents must not contain duplicates")
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("capabilities must not contain duplicates")

        context_fields = [need.field for need in self.context_needs]
        if len(context_fields) != len(set(context_fields)):
            raise ValueError("context fields must not contain duplicates")

        if self.needs_clarification:
            if not self.clarification_question:
                raise ValueError("clarification requires a question")
            if not any(
                need.source == ContextSource.USER_CLARIFICATION
                for need in self.context_needs
            ):
                raise ValueError("clarification requires user-provided context")
        elif self.clarification_question is not None:
            raise ValueError("a clarification question requires needs_clarification")

        return self
