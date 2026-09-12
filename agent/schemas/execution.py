from typing import Self

from pydantic import Field, model_validator

from .planning import Capability, ContextField, GeminiContractModel


class ContextResolution(GeminiContractModel):
    """Context fields grouped by how they can be obtained."""

    resolved_fields: list[ContextField] = Field(default_factory=list)
    deferred_fields: list[ContextField] = Field(default_factory=list)
    missing_fields: list[ContextField] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_partitions(self) -> Self:
        groups = [
            self.resolved_fields,
            self.deferred_fields,
            self.missing_fields,
        ]
        for group in groups:
            if len(group) != len(set(group)):
                raise ValueError("context groups must not contain duplicates")

        all_fields = [field for group in groups for field in group]
        if len(all_fields) != len(set(all_fields)):
            raise ValueError("a context field must belong to only one group")
        return self


class ExecutionStep(GeminiContractModel):
    step_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    capability: Capability
    purpose: str = Field(min_length=1, max_length=200)
    depends_on: list[str] = Field(default_factory=list)
    uses_context: list[ContextField] = Field(default_factory=list)
    produces_context: list[ContextField] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_step(self) -> Self:
        if self.step_id in self.depends_on:
            raise ValueError("a step cannot depend on itself")
        for values in (
            self.depends_on,
            self.uses_context,
            self.produces_context,
        ):
            if len(values) != len(set(values)):
                raise ValueError("step lists must not contain duplicates")
        return self


class ExecutionPlan(GeminiContractModel):
    """Topologically ordered, non-executable plan produced by Gemini."""

    steps: list[ExecutionStep] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    rationale: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def validate_plan_shape(self) -> Self:
        if self.needs_clarification:
            if self.steps:
                raise ValueError("clarification plans cannot contain execution steps")
            if not self.clarification_question:
                raise ValueError("clarification plans require a question")
            return self

        if self.clarification_question is not None:
            raise ValueError("a clarification question requires needs_clarification")
        if not self.steps:
            raise ValueError("ready plans require at least one step")

        seen: set[str] = set()
        for step in self.steps:
            if step.step_id in seen:
                raise ValueError("step ids must be unique")
            missing_dependencies = set(step.depends_on) - seen
            if missing_dependencies:
                raise ValueError(
                    "dependencies must reference an earlier step: "
                    f"{sorted(missing_dependencies)}"
                )
            seen.add(step.step_id)
        return self
