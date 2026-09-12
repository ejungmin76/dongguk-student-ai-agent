import unittest

from pydantic import ValidationError

from agent.planners import question_analyzer_agent
from agent.schemas import (
    Capability,
    ContextField,
    ContextNeed,
    ContextSource,
    IntentType,
    QuestionAnalysis,
)


class QuestionAnalysisSchemaTests(unittest.TestCase):
    def test_typo_question_can_require_profile_and_knowledge(self):
        analysis = QuestionAnalysis(
            intents=[IntentType.UNIVERSITY_KNOWLEDGE],
            capabilities=[
                Capability.STUDENT_PROFILE,
                Capability.UNIVERSITY_KNOWLEDGE,
            ],
            context_needs=[
                ContextNeed(
                    field=ContextField.PRIMARY_MAJOR,
                    source=ContextSource.STUDENT_PROFILE,
                    reason="전공별 졸업요건을 검색하기 위해 필요하다.",
                ),
                ContextNeed(
                    field=ContextField.ADMISSION_YEAR,
                    source=ContextSource.STUDENT_PROFILE,
                    reason="입학연도별 적용 기준을 확인하기 위해 필요하다.",
                ),
            ],
            rationale="개인 전공 기준의 공식 졸업요건 질문이다.",
        )

        self.assertFalse(analysis.needs_clarification)
        self.assertEqual(
            analysis.capabilities,
            [Capability.STUDENT_PROFILE, Capability.UNIVERSITY_KNOWLEDGE],
        )

    def test_navigation_question_uses_registered_menu_capability(self):
        analysis = QuestionAnalysis(
            intents=[IntentType.NDRIMS_NAVIGATION],
            capabilities=[Capability.NDRIMS_MENU],
            context_needs=[
                ContextNeed(
                    field=ContextField.AUTHENTICATED_STUDENT,
                    source=ContextSource.SESSION,
                    reason="학생에게 허용된 nDRIMS 메뉴를 확인해야 한다.",
                )
            ],
            rationale="수강목록 화면의 위치를 찾는 요청이다.",
        )

        self.assertEqual(analysis.capabilities, [Capability.NDRIMS_MENU])

    def test_personal_schedule_uses_authenticated_context(self):
        analysis = QuestionAnalysis(
            intents=[IntentType.PERSONAL_ACADEMIC],
            capabilities=[Capability.CURRENT_SCHEDULE],
            context_needs=[
                ContextNeed(
                    field=ContextField.AUTHENTICATED_STUDENT,
                    source=ContextSource.SESSION,
                    reason="본인의 수강 정보만 조회해야 한다.",
                ),
                ContextNeed(
                    field=ContextField.CURRENT_TERM,
                    source=ContextSource.SYSTEM_CLOCK,
                    reason="현재 학기 수강 내역을 선택해야 한다.",
                ),
            ],
            rationale="현재 학기 개인 시간표 조회 요청이다.",
        )

        self.assertFalse(analysis.needs_clarification)

    def test_clarification_requires_user_context_need(self):
        with self.assertRaises(ValidationError):
            QuestionAnalysis(
                intents=[IntentType.UNKNOWN],
                capabilities=[],
                needs_clarification=True,
                clarification_question="어느 학기를 말씀하시는 건가요?",
                rationale="대상 학기가 불명확하다.",
            )

    def test_unknown_capability_is_rejected(self):
        with self.assertRaises(ValidationError):
            QuestionAnalysis(
                intents=[IntentType.PERSONAL_ACADEMIC],
                capabilities=["invented_tool"],
                rationale="허용되지 않은 기능이다.",
            )

    def test_duplicate_capabilities_are_rejected(self):
        with self.assertRaises(ValidationError):
            QuestionAnalysis(
                intents=[IntentType.UNIVERSITY_KNOWLEDGE],
                capabilities=[
                    Capability.UNIVERSITY_KNOWLEDGE,
                    Capability.UNIVERSITY_KNOWLEDGE,
                ],
                rationale="중복 기능 요청이다.",
            )


class QuestionAnalyzerAgentTests(unittest.TestCase):
    def test_analyzer_uses_schema_without_direct_tools(self):
        self.assertEqual(question_analyzer_agent.output_schema, QuestionAnalysis)
        self.assertEqual(question_analyzer_agent.output_key, "question_analysis")
        self.assertEqual(question_analyzer_agent.tools, [])
