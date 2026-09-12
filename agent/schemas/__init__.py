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
from .result import ToolResult
from .source import SourceReference, SourceType
from .status import ResultStatus

__all__ = [
    "ActionReference",
    "ActionType",
    "AgentResponse",
    "Capability",
    "ContextField",
    "ContextNeed",
    "ContextSource",
    "ContextResolution",
    "ErrorDetail",
    "ExecutionPlan",
    "ExecutionStep",
    "ResultMeta",
    "ResultStatus",
    "IntentType",
    "QuestionAnalysis",
    "SourceReference",
    "SourceType",
    "ToolResult",
]
