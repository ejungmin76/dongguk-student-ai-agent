import json
import os
import unittest

from pydantic import ValidationError

from agent.responders import build_response_agent_input, response_agent
from agent.responders.response_agent import APP_NAME
from agent.schemas import (
    ActionReference,
    ActionType,
    Capability,
    ContextItem,
    ResponseContext,
    ResponseDraft,
    ResultStatus,
    SourceReference,
    SourceType,
)


class ResponseDraftSchemaTests(unittest.TestCase):
    def test_response_draft_round_trip(self):
        draft = ResponseDraft(
            status=ResultStatus.SUCCESS,
            answer="현재 취득학점은 93학점입니다. 총 졸업 기준은 공식 문서에서 확인했습니다.",
            source_ids=["academic-guide-2026"],
            action_ids=["academic-records"],
        )

        restored = ResponseDraft.model_validate_json(draft.model_dump_json())

        self.assertEqual(restored, draft)

    def test_duplicate_source_or_action_ids_are_rejected(self):
        with self.assertRaises(ValidationError):
            ResponseDraft(
                status=ResultStatus.SUCCESS,
                answer="공식 문서 기준을 안내합니다.",
                source_ids=["guide", "guide"],
            )
        with self.assertRaises(ValidationError):
            ResponseDraft(
                status=ResultStatus.SUCCESS,
                answer="등록된 메뉴를 안내합니다.",
                action_ids=["leave", "leave"],
            )

    def test_clarification_requires_follow_up_question(self):
        with self.assertRaises(ValidationError):
            ResponseDraft(
                status=ResultStatus.CLARIFICATION,
                answer="어떤 학기를 기준으로 확인할까요?",
            )


class ResponseAgentInputTests(unittest.TestCase):
    def setUp(self):
        self.context = ResponseContext(
            status=ResultStatus.PARTIAL,
            items=[
                ContextItem(
                    step_id="profile",
                    capability=Capability.STUDENT_PROFILE,
                    data={"primary_major_name": "컴퓨터·AI학부", "admission_year": 2026},
                )
            ],
            sources=[
                SourceReference(
                    source_id="academic-guide-2026",
                    source_type=SourceType.UNIVERSITY_DOCUMENT,
                    title="2026학년도 학업이수 가이드",
                    url="https://www.dongguk.edu/private-source-url",
                    page=12,
                )
            ],
            actions=[
                ActionReference(
                    action_id="leave-of-absence",
                    action_type=ActionType.NAVIGATE_NDRIMS_MENU,
                    label="학사행정 > 학적변동 > 휴학신청",
                )
            ],
            token_budget=2500,
            estimated_tokens=50,
            truncated=True,
        )

    def test_input_contains_safe_facts_and_id_options_but_no_url(self):
        payload = build_response_agent_input(
            question="휴학 신청은 어디서 해?",
            context=self.context,
        )
        decoded = json.loads(payload)

        self.assertEqual(
            decoded["citation_options"][0]["source_id"],
            "academic-guide-2026",
        )
        self.assertEqual(
            decoded["action_options"][0]["action_id"],
            "leave-of-absence",
        )
        self.assertTrue(decoded["response_context"]["truncated"])
        self.assertNotIn("private-source-url", payload)
        self.assertNotIn("token_budget", decoded["response_context"])


class ResponseAgentConfigurationTests(unittest.TestCase):
    def test_response_agent_uses_structured_draft_without_tools(self):
        self.assertEqual(response_agent.name, "response_agent")
        self.assertEqual(response_agent.output_schema, ResponseDraft)
        self.assertEqual(response_agent.output_key, "response_draft")
        self.assertEqual(response_agent.tools, [])
        self.assertEqual(response_agent.model, os.getenv("GEMINI_AGENT_MODEL", "gemini-3.8-flash"))
        self.assertEqual(APP_NAME, "dongguk_student_response")

