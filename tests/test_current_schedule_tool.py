from datetime import time
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from agent.schemas.status import ResultStatus
from apps.academic.models import CourseMeeting, Enrollment
from apps.academic.repositories import DjangoAcademicRepository
from tools.academic import AcademicToolActor, CurrentScheduleTool, CurrentScheduleToolInput


class CurrentScheduleToolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_academic_data", verbosity=0)
        cls.tool = CurrentScheduleTool(DjangoAcademicRepository())

    def test_returns_only_reference_term_schedule(self):
        result = self.tool.execute(
            CurrentScheduleToolInput(),
            AcademicToolActor(student_number="MOCK-2026-008"),
        )

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.data.year, 2029)
        self.assertEqual(result.data.semester, "second")
        self.assertEqual(result.data.total_credits, Decimal("15"))
        self.assertEqual(len(result.data.courses), 5)
        self.assertTrue(all(item.meetings for item in result.data.courses))

    def test_student_with_no_current_enrollment_gets_empty_schedule(self):
        result = self.tool.execute(
            CurrentScheduleToolInput(),
            AcademicToolActor(student_number="MOCK-2026-007"),
        )

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.data.total_credits, Decimal("0"))
        self.assertEqual(result.data.courses, ())
        self.assertEqual(result.data.conflicts, ())

    def test_overlapping_meetings_return_partial_with_conflict(self):
        enrollments = list(
            Enrollment.objects.filter(
                student__student_number="MOCK-2026-008"
            ).select_related("offering")[:2]
        )
        for enrollment in enrollments:
            meeting = CourseMeeting.objects.get(offering=enrollment.offering)
            meeting.day_of_week = "mon"
            meeting.start_time = time(10, 0)
            meeting.end_time = time(11, 15)
            meeting.save()

        result = self.tool.execute(
            CurrentScheduleToolInput(),
            AcademicToolActor(student_number="MOCK-2026-008"),
        )

        self.assertEqual(result.status, ResultStatus.PARTIAL)
        self.assertEqual(result.errors[0].code, "SCHEDULE_CONFLICT")
        self.assertTrue(result.data.conflicts)

    def test_other_student_is_denied(self):
        result = self.tool.execute(
            CurrentScheduleToolInput(target_student_number="MOCK-2026-002"),
            AcademicToolActor(student_number="MOCK-2026-001"),
        )
        self.assertEqual(result.status, ResultStatus.UNAVAILABLE)
        self.assertEqual(result.errors[0].code, "SCHEDULE_ACCESS_DENIED")
