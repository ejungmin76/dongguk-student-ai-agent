from decimal import Decimal

from pydantic import Field

from agent.schemas.base import ContractModel


class AcademicRecordToolInput(ContractModel):
    target_student_number: str | None = Field(default=None, min_length=1, max_length=20)
    year: int | None = Field(default=None, ge=2000, le=2100)
    semester: str | None = None
    category: str | None = None


class AcademicRecordItem(ContractModel):
    year: int
    semester: str
    course_code: str
    course_name: str
    category: str
    credits_attempted: Decimal
    credits_earned: Decimal
    grade: str
    grade_points: Decimal | None
    attempt_number: int
    is_replaced_by_retaking: bool


class CreditSummary(ContractModel):
    key: str
    attempted_credits: Decimal
    earned_credits: Decimal
    gpa_credits: Decimal
    gpa: Decimal | None


class AcademicRecordToolData(ContractModel):
    student_number: str
    cumulative_gpa: Decimal | None
    gpa_credits: Decimal
    attempted_credits: Decimal
    earned_credits: Decimal
    term_summaries: tuple[CreditSummary, ...]
    category_summaries: tuple[CreditSummary, ...]
    records: tuple[AcademicRecordItem, ...]
