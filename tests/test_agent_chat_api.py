import json
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.utils import timezone

from agent.conversation import DjangoConversationStore
from agent.schemas import AgentResponse, ResultStatus
from apps.conversations.models import ConversationSession, ConversationTurn
from apps.core.services import AgentChatService
from apps.core.streaming import AgentChatStreamService


class FakeAgentRuntime:
    def __init__(self, response=None, error=None):
        self.response = response or AgentResponse(status=ResultStatus.SUCCESS, answer="확인된 정보로 안내합니다.")
        self.error = error
        self.calls = []

    async def run_turn(self, *, user_id, session_id, message):
        self.calls.append({"user_id": user_id, "session_id": session_id, "message": message})
        if self.error:
            raise self.error
        return self.response


class AgentChatServiceTests(TestCase):
    subject = "django-user:42"

    def test_service_persists_paired_turns_and_reuses_the_same_session_for_adk(self):
        runtime = FakeAgentRuntime()
        service = AgentChatService(runtime=runtime)

        first = service.chat(authenticated_subject=self.subject, message="안녕하세요")
        second = service.chat(
            authenticated_subject=self.subject,
            session_id=str(first.session_id),
            message="계속 물어볼게요",
        )

        self.assertEqual(first.session_id, second.session_id)
        self.assertEqual([call["session_id"] for call in runtime.calls], [str(first.session_id)] * 2)
        turns = list(ConversationTurn.objects.filter(session_id=first.session_id).values_list("role", "message"))
        self.assertEqual(turns, [("user", "안녕하세요"), ("assistant", "확인된 정보로 안내합니다."), ("user", "계속 물어볼게요"), ("assistant", "확인된 정보로 안내합니다.")])


class AgentChatApiTests(TestCase):
    def setUp(self):
        self.runtime = FakeAgentRuntime()
        self.service = AgentChatService(runtime=self.runtime)
        self.service_patch = patch("apps.core.views.agent_chat_service", self.service)
        self.service_patch.start()
        self.addCleanup(self.service_patch.stop)

    def post(self, payload, *, content_type="application/json"):
        return self.client.post("/api/chat/", data=json.dumps(payload), content_type=content_type)

    def test_csrf_endpoint_issues_a_token_for_the_nextjs_proxy(self):
        response = self.client.get("/api/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["csrf_token"])

    def test_new_and_follow_up_requests_return_stable_json_and_session_id(self):
        first = self.post({"message": "최대 학점이 몇 학점이야?"})
        self.assertEqual(first.status_code, 200)
        first_data = first.json()
        self.assertEqual(first_data["status"], "success")
        self.assertEqual(first_data["sources"], [])
        self.assertIn("session_id", first_data)

        second = self.post({"message": "그럼 계절학기는?", "session_id": first_data["session_id"]})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["session_id"], first_data["session_id"])

    def test_public_invalid_and_wrong_content_type_requests_are_rejected(self):
        public = self.post({"message": "안녕"})
        self.assertEqual(public.status_code, 200)
        invalid = self.post({"message": "", "unexpected": True})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["error"]["code"], "INVALID_REQUEST")

        media_type = self.post({"message": "안녕"}, content_type="text/plain")
        self.assertEqual(media_type.status_code, 415)
        self.assertEqual(media_type.json()["error"]["code"], "UNSUPPORTED_MEDIA_TYPE")

    def test_expired_and_foreign_sessions_are_not_exposed(self):
        store = DjangoConversationStore()
        self.client.get("/api/csrf/")
        own = store.create_session(authenticated_subject=f"anonymous-browser:{self.client.session.session_key}")
        own.expires_at = timezone.now() - timedelta(seconds=1)
        own.save(update_fields=["expires_at"])
        expired = self.post({"message": "이어서 질문", "session_id": str(own.session_id)})
        self.assertEqual(expired.status_code, 410)
        self.assertEqual(expired.json()["error"]["code"], "SESSION_EXPIRED")

        other_client = Client()
        other_client.get("/api/csrf/")
        other = store.create_session(authenticated_subject=f"anonymous-browser:{other_client.session.session_key}")
        forbidden = self.post({"message": "남의 세션", "session_id": str(other.session_id)})
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["error"]["code"], "SESSION_FORBIDDEN")

    def test_agent_failure_returns_stable_service_error_without_details(self):
        self.service.runtime = FakeAgentRuntime(error=RuntimeError("provider internal detail"))
        response = self.post({"message": "질문"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "AGENT_UNAVAILABLE")
        self.assertNotIn("provider internal detail", response.content.decode())


class AgentChatStreamTests(TestCase):
    def setUp(self):
        self.subject = "django-user:stream"
        self.runtime = FakeAgentRuntime()
        self.chat_service = AgentChatService(runtime=self.runtime)
        self.stream_service = AgentChatStreamService(chat_service=self.chat_service)

    def test_stream_emits_ordered_lifecycle_and_replays_from_event_id(self):
        run = self.stream_service.start(authenticated_subject=self.subject, session_id=None)
        body = b"".join(self.stream_service.generate(run_id=run.run_id, authenticated_subject=self.subject, message="질문")).decode()
        self.assertIn("event: session", body)
        self.assertIn("event: progress", body)
        self.assertIn("event: answer", body)
        self.assertIn("event: complete", body)
        replay = self.stream_service.replay(run_id=run.run_id, authenticated_subject=self.subject, after=2)
        self.assertEqual([event.event_type for event in replay], ["answer", "complete"])

    def test_cancelled_stream_does_not_call_agent_or_persist_answer(self):
        run = self.stream_service.start(authenticated_subject=self.subject, session_id=None)
        self.assertTrue(self.stream_service.cancel(run_id=run.run_id, authenticated_subject=self.subject))
        body = b"".join(self.stream_service.generate(run_id=run.run_id, authenticated_subject=self.subject, message="취소할 질문"))
        self.assertEqual(body, b"")
        self.assertEqual(self.runtime.calls, [])
        self.assertEqual(ConversationTurn.objects.count(), 0)
