from __future__ import annotations

import uuid

from django.db import models


class ConversationSession(models.Model):
    """A short-lived session mapped one-to-one to an ADK session identifier."""

    class Status(models.TextChoices):
        ACTIVE = "active", "활성"
        EXPIRED = "expired", "만료"

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # HMAC of the authenticated student subject. Never store its source value here.
    subject_key = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField(db_index=True)
    last_activity_at = models.DateTimeField(db_index=True)
    version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["subject_key", "last_activity_at"],
                name="conversatio_subject_2eb507_idx",
            )
        ]
        verbose_name = "대화 세션"
        verbose_name_plural = "대화 세션"

    def __str__(self) -> str:
        return f"대화 세션 {self.session_id}"


class ConversationTurn(models.Model):
    """One bounded user or assistant message belonging to a conversation session."""

    class Role(models.TextChoices):
        USER = "user", "사용자"
        ASSISTANT = "assistant", "에이전트"

    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name="turns",
    )
    sequence = models.PositiveIntegerField()
    role = models.CharField(max_length=16, choices=Role.choices)
    message = models.TextField(max_length=2_000)
    # For assistant turns, only server-validated source/action IDs and status are kept.
    response_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "sequence"],
                name="conversation_turn_sequence_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["session", "sequence"],
                name="conversatio_session_7dce4f_idx",
            )
        ]
        verbose_name = "대화 턴"
        verbose_name_plural = "대화 턴"

    def __str__(self) -> str:
        return f"{self.session_id} #{self.sequence} {self.role}"
