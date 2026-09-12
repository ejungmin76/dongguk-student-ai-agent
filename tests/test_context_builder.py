from django.test import SimpleTestCase

from agent.context_builder import ContextBuilder
from agent.schemas import (
    Capability,
    PlanExecutionResult,
    ResultStatus,
    StepExecutionState,
    ToolStepExecution,
)


def source(source_id: str = "academic-guide") -> dict:
    return {
        "source_id": source_id,
        "source_type": "university_document",
        "title": "2026학년도 학업이수 가이드",
        "url": "https://www.dongguk.edu/guide",
        "page": 12,
        "effective_at": "2026-01-01",
    }


def action(action_id: str = "course-registration") -> dict:
    return {
        "action_id": action_id,
        "action_type": "navigate_ndrims_menu",
        "label": "학사행정 > 수강신청",
        "requires_confirmation": False,
    }


def execution(*steps: ToolStepExecution, status: ResultStatus = ResultStatus.SUCCESS):
    return PlanExecutionResult(
        status=status,
        steps=list(steps),
        execution_waves=[[step.step_id for step in steps]],
        duration_ms=10,
    )


class ContextBuilderTests(SimpleTestCase):
    def test_profile_projection_removes_student_identity_and_execution_metadata(self):
        context = ContextBuilder().build(
            execution(
                ToolStepExecution(
                    step_id="profile",
                    capability=Capability.STUDENT_PROFILE,
                    tool_name="get_student_profile",
                    state=StepExecutionState.SUCCESS,
                    duration_ms=2,
                    output={
                        "status": "success",
                        "data": {
                            "student_number": "MOCK-2026-008",
                            "display_name": "가상학생08",
                            "admission_year": 2026,
                            "current_semester": 8,
                            "status": "enrolled",
                            "program_track": "advanced",
                            "primary_major_name": "컴퓨터·AI학부",
                            "secondary_major_name": None,
                        },
                        "meta": {
                            "tool_name": "get_student_profile",
                            "execution_id": "private-id",
                            "duration_ms": 2,
                        },
                    },
                )
            )
        )

        data = context.items[0].data
        self.assertNotIn("student_number", data)
        self.assertNotIn("display_name", data)
        self.assertNotIn("execution_id", data)
        self.assertEqual(data["primary_major_name"], "컴퓨터·AI학부")
        self.assertEqual(context.status, ResultStatus.SUCCESS)

    def test_knowledge_projection_keeps_evidence_and_citable_source_only(self):
        context = ContextBuilder().build(
            execution(
                ToolStepExecution(
                    step_id="knowledge",
                    capability=Capability.UNIVERSITY_KNOWLEDGE,
                    tool_name="search_university_knowledge",
                    state=StepExecutionState.SUCCESS,
                    duration_ms=2,
                    output={
                        "status": "success",
                        "data": {
                            "results": [
                                {
                                    "source_id": "academic-guide",
                                    "heading_path": ["졸업", "이수학점"],
                                    "content": "컴퓨터·AI학부 졸업에 필요한 최소 취득학점입니다.",
                                    "rrf_score": 0.03,
                                    "dense_rank": 1,
                                    "keyword_rank": 2,
                                    "document_title": "2026학년도 학업이수 가이드",
                                    "canonical_url": "https://www.dongguk.edu/guide",
                                    "document_status": "current",
                                    "effective_year": 2026,
                                    "effective_from": "2026-01-01",
                                    "effective_to": None,
                                    "page_start": 12,
                                }
                            ],
                            "dense_duration_ms": 10,
                            "keyword_duration_ms": 2,
                            "fusion_duration_ms": 1,
                        },
                        "sources": [source()],
                    },
                )
            )
        )

        hit = context.items[0].data["results"][0]
        self.assertEqual(hit["source_id"], "academic-guide")
        self.assertIn("content", hit)
        self.assertNotIn("rrf_score", hit)
        self.assertNotIn("canonical_url", hit)
        self.assertEqual(context.sources[0].page, 12)

    def test_sources_and_actions_are_deduplicated_across_tool_results(self):
        shared_source = source()
        shared_action = action()
        context = ContextBuilder().build(
            execution(
                ToolStepExecution(
                    step_id="knowledge",
                    capability=Capability.UNIVERSITY_KNOWLEDGE,
                    state=StepExecutionState.SUCCESS,
                    duration_ms=1,
                    output={
                        "status": "success",
                        "data": {"results": []},
                        "sources": [shared_source],
                        "actions": [shared_action],
                    },
                ),
                ToolStepExecution(
                    step_id="menu",
                    capability=Capability.NDRIMS_MENU,
                    state=StepExecutionState.SUCCESS,
                    duration_ms=1,
                    output={
                        "status": "success",
                        "data": {
                            "requires_user_selection": False,
                            "candidates": [],
                        },
                        "sources": [shared_source],
                        "actions": [shared_action],
                    },
                ),
            )
        )

        self.assertEqual(len(context.sources), 1)
        self.assertEqual(len(context.actions), 1)

    def test_budget_truncates_largest_list_and_reports_omission(self):
        records = [
            {
                "year": 2024,
                "semester": "1",
                "course_code": f"CS{index:03d}",
                "course_name": "자료구조와알고리즘" * 3,
                "category": "전공",
                "credits_attempted": "3",
                "credits_earned": "3",
                "grade": "A+",
                "grade_points": "4.5",
                "attempt_number": 1,
                "is_replaced_by_retaking": False,
            }
            for index in range(12)
        ]
        context = ContextBuilder(token_budget=700).build(
            execution(
                ToolStepExecution(
                    step_id="records",
                    capability=Capability.ACADEMIC_RECORDS,
                    state=StepExecutionState.SUCCESS,
                    duration_ms=1,
                    output={
                        "status": "success",
                        "data": {
                            "student_number": "MOCK-2026-008",
                            "cumulative_gpa": "4.2",
                            "gpa_credits": "30",
                            "attempted_credits": "33",
                            "earned_credits": "30",
                            "term_summaries": [],
                            "category_summaries": [],
                            "records": records,
                        },
                        "sources": [source("academic-db")],
                    },
                )
            )
        )

        self.assertTrue(context.truncated)
        self.assertLessEqual(context.estimated_tokens, context.token_budget)
        self.assertLess(len(context.items[0].data["records"]), len(records))
        self.assertEqual(context.sources[0].source_id, "academic-db")
        self.assertTrue(any("records" in item.path for item in context.omissions))

    def test_partial_execution_preserves_safe_error_and_successful_item(self):
        context = ContextBuilder().build(
            execution(
                ToolStepExecution(
                    step_id="records",
                    capability=Capability.ACADEMIC_RECORDS,
                    state=StepExecutionState.ERROR,
                    duration_ms=1,
                    error={
                        "code": "TOOL_EXECUTION_ERROR",
                        "message": "도구 실행 중 처리되지 않은 오류가 발생했습니다.",
                        "retryable": False,
                    },
                ),
                ToolStepExecution(
                    step_id="schedule",
                    capability=Capability.CURRENT_SCHEDULE,
                    state=StepExecutionState.SUCCESS,
                    duration_ms=1,
                    output={
                        "status": "success",
                        "data": {
                            "student_number": "MOCK-2026-008",
                            "year": 2026,
                            "semester": "1",
                            "total_credits": "15",
                            "courses": [],
                            "conflicts": [],
                        },
                    },
                ),
                status=ResultStatus.PARTIAL,
            )
        )

        self.assertEqual(context.status, ResultStatus.PARTIAL)
        self.assertEqual(len(context.items), 1)
        self.assertNotIn("student_number", context.items[0].data)
        self.assertEqual(context.errors[0].code, "TOOL_EXECUTION_ERROR")

