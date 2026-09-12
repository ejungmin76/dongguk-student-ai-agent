"""Safe query enrichment without model-generated facts or user identifiers."""

from __future__ import annotations

from agent.schemas import (
    AppliedQueryContext,
    ContextField,
    FollowUpMode,
    FollowUpResolution,
    QueryRewriteProposal,
    QueryTarget,
    RewrittenQuery,
)


class QueryRewritePolicyError(ValueError):
    pass


class QueryRewritePolicy:
    """Build query text solely from the raw question and trusted structured values."""

    ALLOWED_FIELDS: dict[QueryTarget, frozenset[ContextField]] = {
        QueryTarget.UNIVERSITY_KNOWLEDGE: frozenset(
            {
                ContextField.PRIMARY_MAJOR,
                ContextField.ADMISSION_YEAR,
                ContextField.TARGET_TERM,
            }
        ),
        QueryTarget.ACADEMIC_RECORDS: frozenset({ContextField.TARGET_TERM}),
        QueryTarget.CURRENT_SCHEDULE: frozenset({ContextField.CURRENT_TERM}),
        QueryTarget.NDRIMS_MENU: frozenset({ContextField.TARGET_SERVICE}),
    }
    DISPLAY_LABELS: dict[ContextField, str] = {
        ContextField.PRIMARY_MAJOR: "전공",
        ContextField.ADMISSION_YEAR: "입학연도",
        ContextField.TARGET_TERM: "대상 학기",
        ContextField.CURRENT_TERM: "현재 학기",
        ContextField.TARGET_SERVICE: "대상 서비스",
    }

    def rewrite(
        self,
        *,
        original_query: str,
        proposal: QueryRewriteProposal,
        trusted_context: dict[ContextField, str | int],
        follow_up: FollowUpResolution | None = None,
    ) -> RewrittenQuery:
        raw = original_query.strip()
        if not raw:
            raise QueryRewritePolicyError("original query is required")

        allowed = self.ALLOWED_FIELDS[proposal.target]
        requested = set(proposal.context_fields)
        if not requested.issubset(allowed):
            raise QueryRewritePolicyError("proposal requested context not allowed for its target")
        if not requested.issubset(trusted_context):
            raise QueryRewritePolicyError("proposal requested unavailable context")

        applied = [
            AppliedQueryContext(field=field, value=str(trusted_context[field]))
            for field in proposal.context_fields
        ]
        # Never inject free-text history. A validated reference is trace metadata only.
        reference = None
        if proposal.include_follow_up_reference and follow_up is not None:
            if follow_up.mode != FollowUpMode.RESOLVED:
                raise QueryRewritePolicyError("only a validated single follow-up can be referenced")
            reference = follow_up.referenced_turn_sequences[0]

        if not applied:
            rewritten = raw
        elif proposal.target in {
            QueryTarget.ACADEMIC_RECORDS,
            QueryTarget.CURRENT_SCHEDULE,
        }:
            # Personal academic context remains structured metadata, not query text.
            rewritten = raw
        else:
            context_lines = "\n".join(
                f"- {self.DISPLAY_LABELS[item.field]}: {item.value}" for item in applied
            )
            rewritten = f"{raw}\n[검증된 검색 문맥]\n{context_lines}"

        return RewrittenQuery(
            target=proposal.target,
            original_query=raw,
            rewritten_query=rewritten,
            applied_context=applied,
            referenced_turn_sequence=reference,
            unchanged=rewritten == raw,
        )
