from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from pydantic import BaseModel

from apps.academic.repositories import (
    AcademicRepository,
    DjangoAcademicRepository,
    StudentNotFoundError,
)


class DjangoAcademicRepositoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_academic_data", verbosity=0)
        cls.repository = DjangoAcademicRepository()

    def test_implements_repository_protocol_and_returns_profile_dto(self):
        self.assertIsInstance(self.repository, AcademicRepository)

        profile = self.repository.get_student_profile("MOCK-2026-008")

        self.assertIsInstance(profile, BaseModel)
        self.assertEqual(profile.program_track, "advanced")
        self.assertEqual(profile.primary_major.name, "컴퓨터·AI학부")
        self.assertEqual(profile.reference_term.year, 2029)

    def test_returns_completed_records_as_dtos(self):
        records = self.repository.list_academic_records("MOCK-2026-008")

        self.assertGreaterEqual(sum(item.credits_earned for item in records), Decimal("110"))
        self.assertTrue(all(isinstance(item, BaseModel) for item in records))
        self.assertTrue(any(item.course.code == "CSC4018" for item in records))

    def test_returns_current_enrollments_with_meetings(self):
        enrollments = self.repository.list_current_enrollments("MOCK-2026-008")

        self.assertGreaterEqual(len(enrollments), 4)
        self.assertTrue(any(item.course.code == "CSC4019" for item in enrollments))
        self.assertTrue(all(item.meetings for item in enrollments))

    def test_missing_student_raises_domain_error(self):
        with self.assertRaises(StudentNotFoundError):
            self.repository.get_student_profile("UNKNOWN")
        with self.assertRaises(StudentNotFoundError):
            self.repository.list_academic_records("UNKNOWN")
        with self.assertRaises(StudentNotFoundError):
            self.repository.list_current_enrollments("UNKNOWN")
