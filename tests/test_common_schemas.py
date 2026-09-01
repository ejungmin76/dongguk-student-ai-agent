import unittest
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ValidationError

from agent.schemas import (
    ActionReference,
    ActionType,
    ErrorDetail,
    ResultMeta,
    ResultStatus,
    SourceReference,
    SourceType,
    ToolResult,
)


class SampleAcademicData(BaseModel):
    cumulative_gpa: Decimal
    completed_credits: int


class CommonSchemaTests(unittest.TestCase):
    def setUp(self):
        self.meta = ResultMeta(
            tool_name="get_academic_records",
            execution_id="exec_123",
        )
        self.data = SampleAcademicData(
            cumulative_gpa=Decimal("3.80"),
            completed_credits=112,
        )

    def test_success_result_serializes_and_round_trips(self):
        result = ToolResult[SampleAcademicData](
            status=ResultStatus.SUCCESS,
            data=self.data,
            sources=[
                SourceReference(
                    source_id="academic-records",
                    source_type=SourceType.ACADEMIC_DATABASE,
                    title="Mock Academic Database",
                    effective_at=date(2026, 9, 1),
                )
            ],
            meta=self.meta,
        )

        restored = ToolResult[SampleAcademicData].model_validate_json(
            result.model_dump_json()
        )

        self.assertEqual(restored, result)
        self.assertEqual(restored.status.value, "success")
        self.assertIsInstance(restored.data, SampleAcademicData)

    def test_status_contract_rejects_contradictory_results(self):
        error = ErrorDetail(code="DATABASE_UNAVAILABLE", message="DB unavailable")
        invalid_results = [
            {"status": "success", "data": None, "errors": []},
            {"status": "success", "data": self.data, "errors": [error]},
            {"status": "partial", "data": self.data, "errors": []},
            {"status": "clarification", "data": None, "errors": []},
            {"status": "unavailable", "data": self.data, "errors": [error]},
            {"status": "unavailable", "data": None, "errors": []},
        ]

        for values in invalid_results:
            with self.subTest(status=values["status"]):
                with self.assertRaises(ValidationError):
                    ToolResult[SampleAcademicData](meta=self.meta, **values)

    def test_partial_result_requires_data_and_error(self):
        result = ToolResult[SampleAcademicData](
            status=ResultStatus.PARTIAL,
            data=self.data,
            errors=[
                ErrorDetail(
                    code="GRADUATION_RULE_UNAVAILABLE",
                    message="Graduation rules could not be loaded.",
                    retryable=True,
                )
            ],
            meta=self.meta,
        )

        self.assertEqual(result.status, ResultStatus.PARTIAL)
        self.assertTrue(result.errors[0].retryable)

    def test_open_url_action_requires_http_url(self):
        with self.assertRaises(ValidationError):
            ActionReference(
                action_id="open_registration",
                action_type=ActionType.OPEN_URL,
                label="Open registration",
            )

    def test_confirmation_action_forces_confirmation_flag(self):
        action = ActionReference(
            action_id="confirm_application",
            action_type=ActionType.REQUEST_CONFIRMATION,
            label="Confirm application",
        )

        self.assertTrue(action.requires_confirmation)

    def test_invalid_error_code_and_unknown_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            ErrorDetail(code="database-error", message="Invalid code")

        with self.assertRaises(ValidationError):
            ResultMeta(
                tool_name="get_academic_records",
                execution_id="exec_123",
                unexpected="value",
            )
