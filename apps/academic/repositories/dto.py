from datetime import date, time
from decimal import Decimal

from pydantic import Field

from agent.schemas.base import ContractModel


class MajorDTO(ContractModel):
    code: str
    name: str
    college_name: str


class AcademicTermDTO(ContractModel):
    year: int
    semester: str
    start_date: date
    end_date: date


class StudentProfileDTO(ContractModel):
    student_number: str
    display_name: str
    admission_year: int
    curriculum_year: int
    current_semester: int
    status: str
    program_track: str
    primary_major: MajorDTO
    secondary_major: MajorDTO | None = None
    reference_term: AcademicTermDTO | None = None


class CourseDTO(ContractModel):
    code: str
    name: str
    credits: Decimal = Field(ge=0)
    category: str
    is_english: bool


class CourseMeetingDTO(ContractModel):
    day_of_week: str
    start_time: time
    end_time: time
    classroom: str


class EnrollmentDTO(ContractModel):
    course: CourseDTO
    term: AcademicTermDTO
    section_number: str
    professor_name: str
    status: str
    meetings: tuple[CourseMeetingDTO, ...] = ()


class AcademicRecordDTO(ContractModel):
    course: CourseDTO
    term: AcademicTermDTO
    course_code_snapshot: str
    course_name_snapshot: str
    credits_attempted: Decimal = Field(ge=0)
    credits_earned: Decimal = Field(ge=0)
    grade: str
    grade_points: Decimal | None
    is_passed: bool
    attempt_number: int = Field(ge=1)
    is_replaced_by_retaking: bool
