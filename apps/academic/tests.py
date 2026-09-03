from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.core.management import call_command
from django.test import TestCase

from .choices import GradeCode, Semester
from .models import (
    AcademicRecord,
    AcademicTerm,
    Course,
    CourseOffering,
    Enrollment,
    Major,
    Student,
)


class AcademicModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.major = Major.objects.create(
            code="CSE",
            name="컴퓨터공학과",
            college_name="AI융합대학",
        )
        cls.term = AcademicTerm.objects.create(
            year=2026,
            semester=Semester.FIRST,
            start_date=date(2026, 3, 2),
            end_date=date(2026, 6, 19),
            is_current=True,
        )
        cls.student = Student.objects.create(
            student_number="20260001",
            display_name="테스트 학생",
            admission_year=2026,
            primary_major=cls.major,
            current_semester=1,
        )
        cls.course = Course.objects.create(
            code="CSE2001",
            name="자료구조",
            default_credits=Decimal("3.0"),
            offering_major=cls.major,
        )
        cls.offering = CourseOffering.objects.create(
            course=cls.course,
            term=cls.term,
            section_number="01",
            credits=Decimal("3.0"),
        )

    def test_academic_relationships_are_connected(self):
        enrollment = Enrollment.objects.create(
            student=self.student,
            offering=self.offering,
        )

        self.assertEqual(enrollment.offering.course, self.course)
        self.assertEqual(self.student.enrollments.get(), enrollment)
        self.assertEqual(self.course.offerings.get(), self.offering)

    def test_student_cannot_have_duplicate_enrollment(self):
        Enrollment.objects.create(
            student=self.student,
            offering=self.offering,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Enrollment.objects.create(
                    student=self.student,
                    offering=self.offering,
                )

    def test_academic_record_accepts_matching_offering(self):
        record = AcademicRecord(
            student=self.student,
            course=self.course,
            term=self.term,
            offering=self.offering,
            course_code_snapshot=self.course.code,
            course_name_snapshot=self.course.name,
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("3.0"),
            grade=GradeCode.A_PLUS,
            grade_points=Decimal("4.5"),
            is_passed=True,
        )

        record.full_clean()
        record.save()

        self.assertEqual(record.offering.course, record.course)
        self.assertEqual(record.offering.term, record.term)

    def test_academic_record_rejects_mismatched_offering(self):
        other_course = Course.objects.create(
            code="CSE2002",
            name="알고리즘",
            default_credits=Decimal("3.0"),
            offering_major=self.major,
        )
        record = AcademicRecord(
            student=self.student,
            course=other_course,
            term=self.term,
            offering=self.offering,
            course_code_snapshot=other_course.code,
            course_name_snapshot=other_course.name,
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("3.0"),
            grade=GradeCode.A_PLUS,
            grade_points=Decimal("4.5"),
            is_passed=True,
        )

        with self.assertRaises(ValidationError):
            record.full_clean()


class SeedAcademicDataCommandTests(TestCase):
    def test_seed_creates_safe_mock_scenarios_idempotently(self):
        call_command("seed_academic_data", verbosity=0)
        call_command("seed_academic_data", verbosity=0)

        mock_students = Student.objects.filter(student_number__startswith="MOCK-")
        self.assertEqual(mock_students.count(), 8)
        self.assertTrue(Course.objects.filter(code="CSC2007", name="자료구조").exists())
        self.assertTrue(Course.objects.filter(code="CSC4019", name="종합설계2").exists())
        self.assertTrue(
            mock_students.filter(secondary_major__code="DS").exists()
        )
        self.assertTrue(
            mock_students.filter(status="leave").exists()
        )
        self.assertTrue(
            AcademicRecord.objects.filter(is_replaced_by_retaking=True).exists()
        )
        retake_student = Student.objects.get(student_number="MOCK-2026-006")
        self.assertEqual(
            retake_student.academic_records.filter(course__code="CSC2002").count(),
            2,
        )
        graduating_student = Student.objects.get(student_number="MOCK-2026-008")
        earned = sum(
            record.credits_earned
            for record in graduating_student.academic_records.all()
        )
        self.assertGreaterEqual(earned, Decimal("110.0"))
        self.assertGreaterEqual(graduating_student.enrollments.count(), 4)

        for student in mock_students:
            self.assertTrue(student.display_name.startswith("가상학생"))
