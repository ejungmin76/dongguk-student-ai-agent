from django.core.management import call_command
from django.test import TestCase

from agent.schemas.status import ResultStatus
from apps.academic.repositories import DjangoAcademicRepository
from tools.academic import (
    AcademicToolActor,
    StudentProfileTool,
    StudentProfileToolInput,
    build_get_student_profile_tool,
)


class StudentProfileToolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_academic_data", verbosity=0)
        cls.tool = StudentProfileTool(DjangoAcademicRepository())

    def test_student_can_read_own_minimal_profile(self):
        result = self.tool.execute(
            StudentProfileToolInput(),
            AcademicToolActor(student_number="MOCK-2026-008"),
        )

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.data.primary_major_name, "컴퓨터·AI학부")
        self.assertEqual(result.data.current_semester, 8)
        self.assertEqual(
            set(result.data.model_dump()),
            {
                "student_number", "display_name", "admission_year",
                "current_semester", "status", "program_track",
                "primary_major_name", "secondary_major_name",
            },
        )

    def test_student_cannot_read_another_profile(self):
        result = self.tool.execute(
            StudentProfileToolInput(target_student_number="MOCK-2026-002"),
            AcademicToolActor(student_number="MOCK-2026-001"),
        )

        self.assertEqual(result.status, ResultStatus.UNAVAILABLE)
        self.assertEqual(result.errors[0].code, "PROFILE_ACCESS_DENIED")
        self.assertIsNone(result.data)

    def test_unauthenticated_request_is_rejected(self):
        result = self.tool.execute(
            StudentProfileToolInput(), AcademicToolActor()
        )

        self.assertEqual(result.status, ResultStatus.UNAVAILABLE)
        self.assertEqual(result.errors[0].code, "AUTHENTICATION_REQUIRED")

    def test_missing_authenticated_student_is_unavailable(self):
        result = self.tool.execute(
            StudentProfileToolInput(),
            AcademicToolActor(student_number="MOCK-UNKNOWN"),
        )

        self.assertEqual(result.status, ResultStatus.UNAVAILABLE)
        self.assertEqual(result.errors[0].code, "STUDENT_NOT_FOUND")

    def test_adk_compatible_function_returns_json_dictionary(self):
        function_tool = build_get_student_profile_tool(
            AcademicToolActor(student_number="MOCK-2026-001")
        )

        result = function_tool()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["student_number"], "MOCK-2026-001")
        self.assertEqual(result["meta"]["tool_name"], "get_student_profile")
