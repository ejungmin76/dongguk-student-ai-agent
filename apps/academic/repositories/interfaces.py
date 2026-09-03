from typing import Protocol, runtime_checkable

from .dto import AcademicRecordDTO, EnrollmentDTO, StudentProfileDTO


class StudentNotFoundError(LookupError):
    def __init__(self, student_number: str):
        self.student_number = student_number
        super().__init__(f"학생을 찾을 수 없습니다: {student_number}")


@runtime_checkable
class AcademicRepository(Protocol):
    def get_student_profile(self, student_number: str) -> StudentProfileDTO: ...

    def list_academic_records(self, student_number: str) -> tuple[AcademicRecordDTO, ...]: ...

    def list_current_enrollments(self, student_number: str) -> tuple[EnrollmentDTO, ...]: ...
