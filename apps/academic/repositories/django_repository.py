from django.db.models import Prefetch

from apps.academic.choices import EnrollmentStatus
from apps.academic.models import AcademicRecord, CourseMeeting, Enrollment, Student

from .dto import (
    AcademicRecordDTO, AcademicTermDTO, CourseDTO, CourseMeetingDTO,
    EnrollmentDTO, MajorDTO, StudentProfileDTO,
)
from .interfaces import StudentNotFoundError


class DjangoAcademicRepository:
    """Django ORM 모델을 조회 전용 DTO로 변환하는 adapter."""

    def get_student_profile(self, student_number: str) -> StudentProfileDTO:
        try:
            student = Student.objects.select_related(
                "primary_major", "secondary_major", "reference_term"
            ).get(student_number=student_number)
        except Student.DoesNotExist as exc:
            raise StudentNotFoundError(student_number) from exc

        return StudentProfileDTO(
            student_number=student.student_number,
            display_name=student.display_name,
            admission_year=student.admission_year,
            curriculum_year=student.curriculum_year,
            current_semester=student.current_semester,
            status=student.status,
            program_track=student.program_track,
            primary_major=self._major(student.primary_major),
            secondary_major=self._major(student.secondary_major) if student.secondary_major else None,
            reference_term=self._term(student.reference_term) if student.reference_term else None,
        )

    def list_academic_records(self, student_number: str) -> tuple[AcademicRecordDTO, ...]:
        self._require_student(student_number)
        records = AcademicRecord.objects.filter(
            student__student_number=student_number
        ).select_related("course", "term").order_by(
            "term__year", "term__semester", "course_code_snapshot", "attempt_number"
        )
        return tuple(
            AcademicRecordDTO(
                course=self._course(record.course, record.credits_attempted),
                term=self._term(record.term),
                course_code_snapshot=record.course_code_snapshot,
                course_name_snapshot=record.course_name_snapshot,
                credits_attempted=record.credits_attempted,
                credits_earned=record.credits_earned,
                grade=record.grade,
                grade_points=record.grade_points,
                is_passed=record.is_passed,
                attempt_number=record.attempt_number,
                is_replaced_by_retaking=record.is_replaced_by_retaking,
            )
            for record in records
        )

    def list_current_enrollments(self, student_number: str) -> tuple[EnrollmentDTO, ...]:
        self._require_student(student_number)
        enrollments = Enrollment.objects.filter(
            student__student_number=student_number,
            status=EnrollmentStatus.ENROLLED,
        ).select_related("offering__course", "offering__term").prefetch_related(
            Prefetch(
                "offering__meetings",
                queryset=CourseMeeting.objects.order_by("day_of_week", "start_time"),
            )
        ).order_by("offering__course__code")
        return tuple(
            EnrollmentDTO(
                course=self._course(item.offering.course, item.offering.credits),
                term=self._term(item.offering.term),
                section_number=item.offering.section_number,
                professor_name=item.offering.professor_name,
                status=item.status,
                meetings=tuple(
                    CourseMeetingDTO(
                        day_of_week=meeting.day_of_week,
                        start_time=meeting.start_time,
                        end_time=meeting.end_time,
                        classroom=meeting.classroom,
                    )
                    for meeting in item.offering.meetings.all()
                ),
            )
            for item in enrollments
        )

    @staticmethod
    def _require_student(student_number: str) -> None:
        if not Student.objects.filter(student_number=student_number).exists():
            raise StudentNotFoundError(student_number)

    @staticmethod
    def _major(major) -> MajorDTO:
        return MajorDTO(code=major.code, name=major.name, college_name=major.college_name)

    @staticmethod
    def _term(term) -> AcademicTermDTO:
        return AcademicTermDTO(
            year=term.year, semester=term.semester,
            start_date=term.start_date, end_date=term.end_date,
        )

    @staticmethod
    def _course(course, credits) -> CourseDTO:
        return CourseDTO(
            code=course.code, name=course.name, credits=credits,
            category=course.category, is_english=course.is_english,
        )
