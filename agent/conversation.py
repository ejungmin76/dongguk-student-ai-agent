"""Django-backed, privacy-bounded state shared with the ADK turn runtime."""

from __future__ import annotations

import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.conversations.models import ConversationSession, ConversationTurn

from .schemas import ConversationHistoryTurn, ConversationTurnRole, FollowUpCandidate, FollowUpMode, FollowUpResolution


class ConversationAccessError(ValueError):
    """The requested session does not belong to the authenticated subject."""


class ConversationExpiredError(ValueError):
    """The requested session has expired and must not be resumed."""


class DjangoConversationStore:
    """Own session lifecycle, bounded history, and ADK-compatible session IDs."""

    TTL = timedelta(hours=24)
    MAX_TURNS = 12
    HISTORY_MESSAGE_LIMIT = 500

    @staticmethod
    def subject_key(authenticated_subject: str) -> str:
        if not authenticated_subject or not authenticated_subject.strip():
            raise ValueError("authenticated_subject is required")
        return hmac.new(settings.SECRET_KEY.encode(), authenticated_subject.strip().encode(), hashlib.sha256).hexdigest()

    def create_session(self, *, authenticated_subject: str) -> ConversationSession:
        now = timezone.now()
        return ConversationSession.objects.create(subject_key=self.subject_key(authenticated_subject), expires_at=now + self.TTL, last_activity_at=now)

    def append_turn(self, *, session_id: str, authenticated_subject: str, role: ConversationTurn.Role, message: str, response_metadata: dict | None = None) -> ConversationTurn:
        normalized_message = message.strip()
        if not normalized_message or len(normalized_message) > 2_000:
            raise ValueError("message must contain 1 to 2,000 characters")
        safe_metadata = response_metadata or {}
        if len(str(safe_metadata)) > 4_000:
            raise ValueError("response metadata exceeds the session size limit")
        expired = False
        with transaction.atomic():
            session = ConversationSession.objects.select_for_update().get(session_id=session_id)
            self._assert_owned(session, authenticated_subject)
            if self._is_expired(session):
                session.status = ConversationSession.Status.EXPIRED
                session.save(update_fields=["status", "updated_at"])
                expired = True
            else:
                next_sequence = session.turns.order_by("-sequence").values_list("sequence", flat=True).first() or 0
                turn = ConversationTurn.objects.create(session=session, sequence=next_sequence + 1, role=role, message=normalized_message, response_metadata=safe_metadata)
                session.last_activity_at = timezone.now()
                session.version += 1
                session.save(update_fields=["last_activity_at", "version", "updated_at"])
                self._trim_turns(session)
        if expired:
            raise ConversationExpiredError("session has expired")
        return turn

    def history(self, *, session_id: str, authenticated_subject: str) -> list[ConversationHistoryTurn]:
        session = ConversationSession.objects.get(session_id=session_id)
        self._assert_owned_active(session, authenticated_subject)
        turns = list(session.turns.order_by("-sequence")[: self.MAX_TURNS])
        return [ConversationHistoryTurn(sequence=turn.sequence, role=turn.role, message=turn.message[: self.HISTORY_MESSAGE_LIMIT]) for turn in reversed(turns)]

    def expire_inactive_sessions(self) -> int:
        return ConversationSession.objects.filter(status=ConversationSession.Status.ACTIVE, expires_at__lte=timezone.now()).update(status=ConversationSession.Status.EXPIRED)

    def _assert_owned_active(self, session: ConversationSession, authenticated_subject: str) -> None:
        self._assert_owned(session, authenticated_subject)
        if self._is_expired(session):
            if session.status == ConversationSession.Status.ACTIVE:
                ConversationSession.objects.filter(session_id=session.session_id).update(status=ConversationSession.Status.EXPIRED)
            raise ConversationExpiredError("session has expired")

    def _assert_owned(self, session: ConversationSession, authenticated_subject: str) -> None:
        if not hmac.compare_digest(session.subject_key, self.subject_key(authenticated_subject)):
            raise ConversationAccessError("session ownership does not match")

    @staticmethod
    def _is_expired(session: ConversationSession) -> bool:
        return session.status != ConversationSession.Status.ACTIVE or session.expires_at <= timezone.now()

    def _trim_turns(self, session: ConversationSession) -> None:
        overflow_ids = list(session.turns.order_by("-sequence").values_list("id", flat=True)[self.MAX_TURNS:])
        if overflow_ids:
            ConversationTurn.objects.filter(id__in=overflow_ids).delete()


class FollowUpResolverPolicy:
    """Validate a model-selected prior exchange before the planner sees it."""

    MIN_RESOLUTION_CONFIDENCE = 0.78
    AMBIGUOUS_QUESTION = "이전 대화 중 어떤 내용을 이어서 말씀하신 건가요?"

    @staticmethod
    def candidates(history: list[ConversationHistoryTurn]) -> list[FollowUpCandidate]:
        candidates: list[FollowUpCandidate] = []
        for index, turn in enumerate(history):
            if turn.role != ConversationTurnRole.USER:
                continue
            assistant_message = None
            if index + 1 < len(history) and history[index + 1].role == ConversationTurnRole.ASSISTANT:
                assistant_message = history[index + 1].message
            candidates.append(FollowUpCandidate(turn_sequence=turn.sequence, user_message=turn.message, assistant_message=assistant_message))
        return candidates

    def validate(self, resolution: FollowUpResolution, *, candidates: list[FollowUpCandidate]) -> FollowUpResolution:
        candidate_ids = {candidate.turn_sequence for candidate in candidates}
        if not set(resolution.referenced_turn_sequences).issubset(candidate_ids):
            return self._clarification(candidates)
        if resolution.mode == FollowUpMode.RESOLVED and resolution.confidence < self.MIN_RESOLUTION_CONFIDENCE:
            return self._clarification(candidates)
        if resolution.mode == FollowUpMode.CLARIFICATION:
            return self._clarification(candidates, resolution.referenced_turn_sequences)
        return resolution

    def _clarification(self, candidates: list[FollowUpCandidate], references: list[int] | None = None) -> FollowUpResolution:
        candidate_ids = [candidate.turn_sequence for candidate in candidates]
        if not candidate_ids:
            return FollowUpResolution(
                mode=FollowUpMode.STANDALONE,
                confidence=1,
                rationale="이전 대화 후보가 없어 독립 질문으로 처리한다.",
            )
        return FollowUpResolution(
            mode=FollowUpMode.CLARIFICATION,
            referenced_turn_sequences=references or candidate_ids[-2:],
            confidence=0,
            rationale=self.AMBIGUOUS_QUESTION,
        )
