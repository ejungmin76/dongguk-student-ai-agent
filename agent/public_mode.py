"""Public deployment boundary: personal academic capabilities stay isolated."""

from agent.schemas import Capability, ExecutionPlan

PUBLIC_CAPABILITIES = frozenset({Capability.UNIVERSITY_KNOWLEDGE, Capability.NDRIMS_MENU, Capability.GENERAL_RESPONSE})


def assert_public_plan(plan: ExecutionPlan) -> None:
    private = {step.capability for step in plan.steps} - PUBLIC_CAPABILITIES
    if private:
        raise PermissionError(f"public mode does not allow: {sorted(private)}")
