from datetime import time
from decimal import Decimal

from pydantic import Field

from agent.schemas.base import ContractModel


class CurrentScheduleToolInput(ContractModel):
    target_student_number: str | None = Field(default=None, min_length=1, max_length=20)


class MeetingItem(ContractModel):
    day_of_week: str
    start_time: time
    end_time: time
    classroom: str


class CurrentCourseItem(ContractModel):
    course_code: str
    course_name: str
    category: str
    credits: Decimal
    section_number: str
    professor_name: str
    meetings: tuple[MeetingItem, ...]


class ScheduleConflict(ContractModel):
    day_of_week: str
    first_course_code: str
    second_course_code: str
    overlap_start: time
    overlap_end: time


class CurrentScheduleToolData(ContractModel):
    student_number: str
    year: int | None
    semester: str | None
    total_credits: Decimal
    courses: tuple[CurrentCourseItem, ...]
    conflicts: tuple[ScheduleConflict, ...]
