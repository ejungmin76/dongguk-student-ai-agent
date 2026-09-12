"""Persisted SSE lifecycle events for the authenticated chat API."""

import json

from django.db import transaction

from apps.conversations.models import ConversationSession, ConversationStreamEvent, ConversationStreamRun


def encode_sse(event: ConversationStreamEvent) -> bytes:
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event_type}\n"
        f"data: {json.dumps(event.payload, ensure_ascii=False, default=str)}\n\n"
    ).encode()


class AgentChatStreamService:
    MAX_EVENTS = 32

    def __init__(self, *, chat_service):
        self.chat_service = chat_service

    def start(self, *, authenticated_subject: str, session_id: str | None) -> ConversationStreamRun:
        store = self.chat_service.conversation_store
        if session_id is None:
            session = store.create_session(authenticated_subject=authenticated_subject)
        else:
            store.history(session_id=session_id, authenticated_subject=authenticated_subject)
            session = ConversationSession.objects.get(session_id=session_id)
        return ConversationStreamRun.objects.create(session=session)

    def emit(self, run_id, event_type: str, payload: dict) -> ConversationStreamEvent | None:
        with transaction.atomic():
            run = ConversationStreamRun.objects.select_for_update().get(run_id=run_id)
            if run.status == ConversationStreamRun.Status.CANCELED:
                return None
            event = ConversationStreamEvent.objects.create(run=run, sequence=run.next_sequence, event_type=event_type, payload=payload)
            run.next_sequence += 1
            run.save(update_fields=["next_sequence", "updated_at"])
            old_ids = list(run.events.order_by("-sequence").values_list("id", flat=True)[self.MAX_EVENTS:])
            if old_ids:
                ConversationStreamEvent.objects.filter(id__in=old_ids).delete()
            return event

    def cancel(self, *, run_id, authenticated_subject: str) -> bool:
        with transaction.atomic():
            run = ConversationStreamRun.objects.select_for_update().select_related("session").get(run_id=run_id)
            self.chat_service.conversation_store._assert_owned_active(run.session, authenticated_subject)
            if run.status != ConversationStreamRun.Status.RUNNING:
                return False
            run.status = ConversationStreamRun.Status.CANCELED
            run.save(update_fields=["status", "updated_at"])
            return True

    def replay(self, *, run_id, authenticated_subject: str, after: int) -> list[ConversationStreamEvent]:
        run = ConversationStreamRun.objects.select_related("session").get(run_id=run_id)
        self.chat_service.conversation_store._assert_owned_active(run.session, authenticated_subject)
        return list(run.events.filter(sequence__gt=after).order_by("sequence"))

    def generate(self, *, run_id, authenticated_subject: str, message: str):
        run = ConversationStreamRun.objects.select_related("session").get(run_id=run_id)
        event = self.emit(run_id, "session", {"session_id": str(run.session_id), "stream_id": str(run_id)})
        if event:
            yield encode_sse(event)
        event = self.emit(run_id, "progress", {"phase": "answer_preparing"})
        if event:
            yield encode_sse(event)
        if ConversationStreamRun.objects.filter(run_id=run_id, status=ConversationStreamRun.Status.CANCELED).exists():
            return
        try:
            response = self.chat_service.chat(authenticated_subject=authenticated_subject, message=message, session_id=str(run.session_id))
        except (RuntimeError, TypeError):
            ConversationStreamRun.objects.filter(run_id=run_id).update(status=ConversationStreamRun.Status.FAILED)
            event = self.emit(run_id, "error", {"code": "AGENT_UNAVAILABLE", "message": "현재 답변을 준비하지 못했습니다."})
            if event:
                yield encode_sse(event)
            return
        if ConversationStreamRun.objects.filter(run_id=run_id, status=ConversationStreamRun.Status.CANCELED).exists():
            return
        event = self.emit(run_id, "answer", {"text": response.answer})
        if event:
            yield encode_sse(event)
        for source in response.sources:
            event = self.emit(run_id, "source", source.model_dump(mode="json"))
            if event:
                yield encode_sse(event)
        for action in response.actions:
            event = self.emit(run_id, "action", action.model_dump(mode="json"))
            if event:
                yield encode_sse(event)
        event = self.emit(run_id, "complete", {"status": response.status, "limitations": response.limitations, "follow_up_question": response.follow_up_question})
        if event:
            yield encode_sse(event)
        ConversationStreamRun.objects.filter(run_id=run_id, status=ConversationStreamRun.Status.RUNNING).update(status=ConversationStreamRun.Status.COMPLETED)
