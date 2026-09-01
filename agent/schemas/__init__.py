"""Structured contracts shared by tools and the agent runtime."""

from .action import ActionReference, ActionType
from .error import ErrorDetail
from .meta import ResultMeta
from .result import ToolResult
from .source import SourceReference, SourceType
from .status import ResultStatus

__all__ = [
    "ActionReference",
    "ActionType",
    "ErrorDetail",
    "ResultMeta",
    "ResultStatus",
    "SourceReference",
    "SourceType",
    "ToolResult",
]
