import json
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from agent.conversation import ConversationAccessError, ConversationExpiredError, DjangoConversationStore, FollowUpResolverPolicy
from agent.planners import build_follow_up_resolver_input, follow_up_resolver_agent
from agent.schemas import ConversationTurnRole, FollowUpMode, FollowUpResolution
from apps.conversations.models import ConversationSession, ConversationTurn


class ConversationStoreTests(TestCase):
    subject = "mock-authenticated-student-8"

    def setUp(self):
        self.store = DjangoConversationStore()
        self.session = self.store.create_session(authenticated_subject=self.subject)

    def test_session_uses_hmac_subject_and_shared_adk_session_id(self):
        self.assertNotEqual(self.session.subject_key, self.subject)
        self.assertEqual(len(self.session.subject_key), 64)
        self.assertEqual(str(self.session.session_id), str(self.session.session_id))

    def test_append_assigns_serial_turns_and_keeps_only_recent_bounded_history(self):
        for index in range(14):
            self.store.append_turn(session_id=str(self.session.session_id), authenticated_subject=self.subject, role=ConversationTurn.Role.USER, message=f"질문 {index}")

        history = self.store.history(session_id=str(self.session.session_id), authenticated_subject=self.subject)
        self.session.refresh_from_db()
        self.assertEqual(self.session.version, 14)
        self.assertEqual(len(history), 12)
        self.assertEqual([turn.sequence for turn in history], list(range(3, 15)))
        self.assertEqual(ConversationTurn.objects.filter(session=self.session).count(), 12)

    def test_wrong_subject_cannot_read_or_append_turns(self):
        with self.assertRaises(ConversationAccessError):
            self.store.history(session_id=str(self.session.session_id), authenticated_subject="another-student")
        with self.assertRaises(ConversationAccessError):
            self.store.append_turn(session_id=str(self.session.session_id), authenticated_subject="another-student", role=ConversationTurn.Role.USER, message="내 시간표 보여줘")

    def test_expired_session_is_marked_and_cannot_resume(self):
        self.session.expires_at = timezone.now() - timedelta(seconds=1)
        self.session.save(update_fields=["expires_at"])
        with self.assertRaises(ConversationExpiredError):
            self.store.append_turn(session_id=str(self.session.session_id), authenticated_subject=self.subject, role=ConversationTurn.Role.USER, message="이전 질문 계속할게")
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, ConversationSession.Status.EXPIRED)


class FollowUpResolverTests(TestCase):
    subject = "mock-authenticated-student-8"

    def setUp(self):
        self.store = DjangoConversationStore()
        self.session = self.store.create_session(authenticated_subject=self.subject)
        for role, message in (
            (ConversationTurn.Role.USER, "컴퓨터·AI학부 졸업학점 알려줘"),
            (ConversationTurn.Role.ASSISTANT, "공식 가이드 기준을 확인해 안내할게요."),
            (ConversationTurn.Role.USER, "기숙사 신청 메뉴도 찾아줘"),
            (ConversationTurn.Role.ASSISTANT, "등록된 nDRIMS 메뉴에서 찾을게요."),
        ):
            self.store.append_turn(session_id=str(self.session.session_id), authenticated_subject=self.subject, role=role, message=message)
        self.history = self.store.history(session_id=str(self.session.session_id), authenticated_subject=self.subject)
        self.policy = FollowUpResolverPolicy()
        self.candidates = self.policy.candidates(self.history)

    def test_candidates_are_server_derived_user_exchanges_only(self):
        self.assertEqual([candidate.turn_sequence for candidate in self.candidates], [1, 3])
        self.assertEqual(self.candidates[0].assistant_message, "공식 가이드 기준을 확인해 안내할게요.")

    def test_confident_single_reference_is_accepted(self):
        resolution = FollowUpResolution(mode=FollowUpMode.RESOLVED, referenced_turn_sequences=[1], confidence=0.91, rationale="바로 앞의 졸업학점 대상을 이어서 묻는다.")
        self.assertEqual(self.policy.validate(resolution, candidates=self.candidates), resolution)

    def test_ambiguous_or_low_confidence_reference_becomes_server_clarification(self):
        low_confidence = FollowUpResolution(mode=FollowUpMode.RESOLVED, referenced_turn_sequences=[1], confidence=0.5, rationale="후속 질문일 가능성이 있다.")
        result = self.policy.validate(low_confidence, candidates=self.candidates)
        self.assertEqual(result.mode, FollowUpMode.CLARIFICATION)
        self.assertEqual(result.rationale, self.policy.AMBIGUOUS_QUESTION)
        self.assertEqual(result.referenced_turn_sequences, [1, 3])

    def test_unknown_turn_reference_is_never_accepted(self):
        resolution = FollowUpResolution(mode=FollowUpMode.RESOLVED, referenced_turn_sequences=[99], confidence=0.99, rationale="존재하지 않는 후보를 참조한다.")
        result = self.policy.validate(resolution, candidates=self.candidates)
        self.assertEqual(result.mode, FollowUpMode.CLARIFICATION)
        self.assertEqual(result.referenced_turn_sequences, [1, 3])

    def test_no_history_never_produces_a_fake_reference(self):
        resolution = FollowUpResolution(
            mode=FollowUpMode.RESOLVED,
            referenced_turn_sequences=[99],
            confidence=0.99,
            rationale="존재하지 않는 후보를 참조한다.",
        )
        result = self.policy.validate(resolution, candidates=[])
        self.assertEqual(result.mode, FollowUpMode.STANDALONE)
        self.assertEqual(result.referenced_turn_sequences, [])

    def test_resolver_agent_receives_only_current_question_and_server_candidates(self):
        payload = json.loads(build_follow_up_resolver_input(current_question="그럼 전공은 몇 학점이야?", candidates=self.candidates))
        self.assertEqual(payload["current_question"], "그럼 전공은 몇 학점이야?")
        self.assertEqual([item["turn_sequence"] for item in payload["server_candidates"]], [1, 3])
        self.assertEqual(follow_up_resolver_agent.tools, [])
