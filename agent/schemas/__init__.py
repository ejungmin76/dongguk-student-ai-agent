"""Structured contracts shared by tools and the agent runtime."""

from .action import ActionReference, ActionType
from .error import ErrorDetail
from .execution import ContextResolution, ExecutionPlan, ExecutionStep
from .meta import ResultMeta
from .planning import (
    Capability,
    ContextField,
    ContextNeed,
    ContextSource,
    IntentType,
    QuestionAnalysis,
)
from .response import AgentResponse
from .response_context import ContextItem, ContextOmission, ResponseContext
from .response_draft import ResponseDraft
from .result import ToolResult
from .source import SourceReference, SourceType
from .status import ResultStatus
from .tool_execution import (
    PlanExecutionResult,
    StepExecutionState,
    ToolStepExecution,
)

__all__ = [
    "ActionReference",
    "ActionType",
    "AgentResponse",
    "Capability",
    "ContextField",
    "ContextNeed",
    "ContextSource",
    "ContextResolution",
    "ContextItem",
    "ContextOmission",
    "ErrorDetail",
    "ExecutionPlan",
    "ExecutionStep",
    "ResultMeta",
    "ResultStatus",
    "ResponseContext",
    "ResponseDraft",
    "PlanExecutionResult",
    "StepExecutionState",
    "ToolStepExecution",
    "IntentType",
    "QuestionAnalysis",
    "SourceReference",
    "SourceType",
    "ToolResult",
]
