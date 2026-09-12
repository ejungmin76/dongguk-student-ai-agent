"""Deterministic safety validation for model-generated execution plans."""

from agent.schemas import (
    Capability,
    ContextField,
    ContextResolution,
    ExecutionPlan,
    QuestionAnalysis,
)


CAPABILITY_REQUIRED_CONTEXT: dict[Capability, set[ContextField]] = {
    Capability.STUDENT_PROFILE: {ContextField.AUTHENTICATED_STUDENT},
    Capability.ACADEMIC_RECORDS: {ContextField.AUTHENTICATED_STUDENT},
    Capability.CURRENT_SCHEDULE: {ContextField.AUTHENTICATED_STUDENT},
    Capability.UNIVERSITY_KNOWLEDGE: set(),
    Capability.NDRIMS_MENU: set(),
    Capability.GENERAL_RESPONSE: set(),
}

CAPABILITY_PRODUCED_CONTEXT: dict[Capability, set[ContextField]] = {
    Capability.STUDENT_PROFILE: {
        ContextField.PRIMARY_MAJOR,
        ContextField.ADMISSION_YEAR,
    },
    Capability.ACADEMIC_RECORDS: set(),
    Capability.CURRENT_SCHEDULE: {ContextField.CURRENT_TERM},
    Capability.UNIVERSITY_KNOWLEDGE: set(),
    Capability.NDRIMS_MENU: set(),
    Capability.GENERAL_RESPONSE: set(),
}


class InvalidExecutionPlan(ValueError):
    pass


def validate_execution_plan(
    plan: ExecutionPlan,
    *,
    analysis: QuestionAnalysis,
    context_resolution: ContextResolution,
) -> None:
    """Reject capabilities or context flow the model is not allowed to claim."""

    if plan.needs_clarification:
        return

    if context_resolution.missing_fields:
        raise InvalidExecutionPlan(
            "ready plan contains missing context: "
            f"{sorted(context_resolution.missing_fields)}"
        )

    requested = set(analysis.capabilities)
    planned = {step.capability for step in plan.steps}
    unexpected = planned - requested
    omitted = requested - planned
    if unexpected:
        raise InvalidExecutionPlan(
            f"plan contains unrequested capabilities: {sorted(unexpected)}"
        )
    if omitted:
        raise InvalidExecutionPlan(
            f"plan omitted requested capabilities: {sorted(omitted)}"
        )

    initially_available = set(context_resolution.resolved_fields)
    available_after_step: dict[str, set[ContextField]] = {}

    for step in plan.steps:
        allowed_outputs = CAPABILITY_PRODUCED_CONTEXT[step.capability]
        claimed_outputs = set(step.produces_context)
        if not claimed_outputs <= allowed_outputs:
            raise InvalidExecutionPlan(
                f"{step.capability} cannot produce: "
                f"{sorted(claimed_outputs - allowed_outputs)}"
            )

        inherited = set(initially_available)
        for dependency_id in step.depends_on:
            inherited |= available_after_step[dependency_id]

        declared_inputs = set(step.uses_context)
        mandatory_inputs = CAPABILITY_REQUIRED_CONTEXT[step.capability]
        if not mandatory_inputs <= declared_inputs:
            raise InvalidExecutionPlan(
                f"{step.capability} must declare context: "
                f"{sorted(mandatory_inputs - declared_inputs)}"
            )

        unavailable = declared_inputs - inherited
        if unavailable:
            raise InvalidExecutionPlan(
                f"{step.step_id} uses unavailable context: {sorted(unavailable)}"
            )

        available_after_step[step.step_id] = inherited | claimed_outputs

    final_available = set(initially_available)
    for fields in available_after_step.values():
        final_available |= fields
    if not set(context_resolution.deferred_fields) <= final_available:
        raise InvalidExecutionPlan(
            "plan does not produce all deferred context fields: "
            f"{sorted(set(context_resolution.deferred_fields) - final_available)}"
        )
