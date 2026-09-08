from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from agent.schemas.status import ResultStatus
from apps.academic.repositories import DjangoAcademicRepository
from tools.academic import AcademicRecordTool, AcademicRecordToolInput, AcademicToolActor


class AcademicRecordToolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_academic_data", verbosity=0)
        cls.tool = AcademicRecordTool(DjangoAcademicRepository())

    def test_returns_official_cumulative_gpa_and_credits(self):
        result = self.tool.execute(
            AcademicRecordToolInput(),
            AcademicToolActor(student_number="MOCK-2026-008"),
        )

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertGreaterEqual(result.data.earned_credits, Decimal("110"))
        self.assertIsNotNone(result.data.cumulative_gpa)
        self.assertEqual(result.data.gpa_credits, result.data.attempted_credits)
        self.assertGreaterEqual(len(result.data.term_summaries), 7)
        self.assertTrue(result.data.category_summaries)

    def test_filters_by_term_and_category(self):
        result = self.tool.execute(
            AcademicRecordToolInput(year=2026, semester="first", category="major"),
            AcademicToolActor(student_number="MOCK-2026-008"),
        )

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertTrue(result.data.records)
        self.assertTrue(all(item.year == 2026 for item in result.data.records))
        self.assertTrue(all(item.semester == "first" for item in result.data.records))
        self.assertTrue(all(item.category == "major" for item in result.data.records))

    def test_replaced_retake_record_is_not_double_counted(self):
        result = self.tool.execute(
            AcademicRecordToolInput(),
            AcademicToolActor(student_number="MOCK-2026-006"),
        )
        replaced = [item for item in result.data.records if item.is_replaced_by_retaking]

        self.assertEqual(len(replaced), 1)
        expected = sum(
            item.credits_earned
            for item in result.data.records
            if not item.is_replaced_by_retaking
        )
        self.assertEqual(result.data.earned_credits, expected)

    def test_other_student_is_denied(self):
        result = self.tool.execute(
            AcademicRecordToolInput(target_student_number="MOCK-2026-002"),
            AcademicToolActor(student_number="MOCK-2026-001"),
        )
        self.assertEqual(result.status, ResultStatus.UNAVAILABLE)
        self.assertEqual(result.errors[0].code, "ACADEMIC_RECORD_ACCESS_DENIED")
