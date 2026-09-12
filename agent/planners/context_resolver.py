"""Resolve context availability without exposing context values to the planner."""

from collections.abc import Iterable

from agent.schemas import (
    Capability,
    ContextField,
    ContextResolution,
    ContextSource,
    QuestionAnalysis,
)


def resolve_question_context(
    analysis: QuestionAnalysis,
    *,
    session_fields: Iterable[ContextField] = (),
    system_fields: Iterable[ContextField] = (),
) -> ContextResolution:
    """Classify required context as ready, Tool-resolvable, or missing."""

    resolved = set(session_fields) | set(system_fields)
    deferred: set[ContextField] = set()
    missing: set[ContextField] = set()

    for need in analysis.context_needs:
        if need.source == ContextSource.USER_MESSAGE:
            resolved.add(need.field)
        elif need.source == ContextSource.SESSION:
            if need.field not in resolved:
                missing.add(need.field)
        elif need.source == ContextSource.SYSTEM_CLOCK:
            if need.field not in resolved:
                missing.add(need.field)
        elif need.source == ContextSource.STUDENT_PROFILE:
            if Capability.STUDENT_PROFILE in analysis.capabilities:
                deferred.add(need.field)
            else:
                missing.add(need.field)
        elif need.source == ContextSource.USER_CLARIFICATION:
            missing.add(need.field)

    deferred -= resolved
    missing -= resolved | deferred
    return ContextResolution(
        resolved_fields=sorted(resolved, key=str),
        deferred_fields=sorted(deferred, key=str),
        missing_fields=sorted(missing, key=str),
    )
