import os
import unittest

from pydantic import ValidationError

from agent.agent import root_agent
from agent.runtime import APP_NAME
from agent.schemas import AgentResponse, ResultStatus
from google.adk.sessions import InMemorySessionService


class AgentResponseTests(unittest.TestCase):
    def test_response_round_trip(self):
        response = AgentResponse(
            status=ResultStatus.SUCCESS,
            answer="안녕하세요.",
        )

        restored = AgentResponse.model_validate_json(response.model_dump_json())

        self.assertEqual(restored, response)

    def test_clarification_requires_follow_up_question(self):
        with self.assertRaises(ValidationError):
            AgentResponse(
                status=ResultStatus.CLARIFICATION,
                answer="질문을 조금 더 구체적으로 알려주세요.",
            )

    def test_non_clarification_rejects_follow_up_question(self):
        with self.assertRaises(ValidationError):
            AgentResponse(
                status=ResultStatus.SUCCESS,
                answer="처리했습니다.",
                follow_up_question="무엇이 궁금한가요?",
            )


class RootAgentConfigurationTests(unittest.TestCase):
    def test_root_agent_uses_structured_output_without_tools(self):
        self.assertEqual(root_agent.name, "dongguk_student_agent")
        self.assertEqual(root_agent.output_schema, AgentResponse)
        self.assertEqual(root_agent.output_key, "agent_response")
        self.assertEqual(root_agent.tools, [])

    def test_model_can_be_configured_by_environment(self):
        expected = os.getenv("GEMINI_AGENT_MODEL", "gemini-3.8-flash")
        self.assertEqual(root_agent.model, expected)


class InMemorySessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_can_be_created_and_loaded(self):
        service = InMemorySessionService()
        created = await service.create_session(
            app_name=APP_NAME,
            user_id="test-user",
            session_id="test-session",
        )

        loaded = await service.get_session(
            app_name=APP_NAME,
            user_id="test-user",
            session_id="test-session",
        )

        self.assertEqual(created.id, "test-session")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, created.id)
