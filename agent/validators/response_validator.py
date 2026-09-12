"""Deterministic grounding checks for Gemini's structured response draft."""

import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from agent.schemas import (
    ResponseContext,
    ResponseDraft,
    ResultStatus,
    SourceReference,
    SourceType,
    ValidatedResponse,
)


class InvalidResponseDraft(ValueError):
    """Raised when a model draft exceeds its server-provided evidence."""


class ResponseValidator:
    """Resolve approved IDs and reject status or numeric-fact hallucinations."""

    _NUMBER_PATTERN = re.compile(
        r"(?<![A-Za-z_])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![A-Za-z_])"
    )

    def validate(
        self,
        draft: ResponseDraft,
        *,
        context: ResponseContext,
    ) -> ValidatedResponse:
        self._validate_status(draft, context)
        self._validate_limitations(draft, context)
        sources = self._resolve_sources(draft, context)
        actions = self._resolve_actions(draft, context)
        self._validate_numeric_grounding(draft, context)
        return ValidatedResponse.from_draft(
            draft,
            sources=sources,
            actions=actions,
        )

    @staticmethod
    def _validate_status(draft: ResponseDraft, context: ResponseContext) -> None:
        if draft.status != context.status:
            raise InvalidResponseDraft(
                "response status must exactly match the server response context"
            )

    @staticmethod
    def _validate_limitations(draft: ResponseDraft, context: ResponseContext) -> None:
        requires_limitation = context.truncated or context.status in {
            ResultStatus.PARTIAL,
            ResultStatus.UNAVAILABLE,
        }
        if requires_limitation and not draft.limitations:
            raise InvalidResponseDraft(
                "partial, unavailable, or truncated context requires a limitation"
            )

    @staticmethod
    def _resolve_sources(
        draft: ResponseDraft,
        context: ResponseContext,
    ) -> list[SourceReference]:
        source_by_id = {source.source_id: source for source in context.sources}
        resolved: list[SourceReference] = []
        for source_id in draft.source_ids:
            source = source_by_id.get(source_id)
            if source is None:
                raise InvalidResponseDraft(f"unknown source_id: {source_id}")
            if source.source_type == SourceType.UNIVERSITY_DOCUMENT and source.url is None:
                raise InvalidResponseDraft(
                    f"official document source requires a validated URL: {source_id}"
                )
            resolved.append(source)
        return resolved

    @staticmethod
    def _resolve_actions(draft: ResponseDraft, context: ResponseContext):
        action_by_id = {action.action_id: action for action in context.actions}
        resolved = []
        for action_id in draft.action_ids:
            action = action_by_id.get(action_id)
            if action is None:
                raise InvalidResponseDraft(f"unknown action_id: {action_id}")
            resolved.append(action)
        return resolved

    def _validate_numeric_grounding(
        self,
        draft: ResponseDraft,
        context: ResponseContext,
    ) -> None:
        allowed_numbers = self._collect_numbers(
            [item.model_dump(mode="json") for item in context.items]
        )
        text_fields = [draft.answer, *draft.limitations]
        if draft.follow_up_question:
            text_fields.append(draft.follow_up_question)

        for text in text_fields:
            for match in self._NUMBER_PATTERN.findall(text):
                number = self._normalize_number(match)
                if number not in allowed_numbers:
                    raise InvalidResponseDraft(
                        "response contains a numeric fact not present in context: "
                        f"{match}"
                    )

    def _collect_numbers(self, value: Any) -> set[Decimal]:
        numbers: set[Decimal] = set()

        def visit(current: Any) -> None:
            if isinstance(current, bool) or current is None:
                return
            if isinstance(current, (int, float, Decimal)):
                numbers.add(self._normalize_number(str(current)))
                return
            if isinstance(current, str):
                for match in self._NUMBER_PATTERN.findall(current):
                    numbers.add(self._normalize_number(match))
                return
            if isinstance(current, Mapping):
                for child in current.values():
                    visit(child)
                return
            if isinstance(current, (list, tuple)):
                for child in current:
                    visit(child)

        visit(value)
        return numbers

    @staticmethod
    def _normalize_number(value: str) -> Decimal:
        try:
            return Decimal(value.replace(",", "")).normalize()
        except InvalidOperation as error:
            raise InvalidResponseDraft(f"invalid numeric literal: {value}") from error


default_response_validator = ResponseValidator()
