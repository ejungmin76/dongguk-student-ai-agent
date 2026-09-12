from enum import StrEnum
from typing import Any, Self

from pydantic import Field, model_validator

from .base import ContractModel
from .error import ErrorDetail
from .planning import Capability
from .status import ResultStatus


class StepExecutionState(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    CLARIFICATION = "clarification"
    TIMED_OUT = "timed_out"
    ERROR = "error"
    BLOCKED = "blocked"


class ToolStepExecution(ContractModel):
    """Unnormalized result of one server-approved Tool invocation."""

    step_id: str
    capability: Capability
    tool_name: str | None = None
    state: StepExecutionState
    output: dict[str, Any] | None = None
    error: ErrorDetail | None = None
    duration_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_result_shape(self) -> Self:
        failed = {
            StepExecutionState.TIMED_OUT,
            StepExecutionState.ERROR,
            StepExecutionState.BLOCKED,
        }
        if self.state in failed and self.error is None:
            raise ValueError("executor failures require an error")
        if self.state in failed and self.output is not None:
            raise ValueError("executor failures cannot contain Tool output")
        if self.state not in failed and self.output is None:
            raise ValueError("completed Tool steps require output")
        return self

    @property
    def is_usable(self) -> bool:
        return self.state in {
            StepExecutionState.SUCCESS,
            StepExecutionState.PARTIAL,
        }


class PlanExecutionResult(ContractModel):
    """All raw Tool outputs, kept in the original plan order."""

    status: ResultStatus
    steps: list[ToolStepExecution]
    execution_waves: list[list[str]]
    duration_ms: int = Field(ge=0)

