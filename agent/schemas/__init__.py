"""Structured contracts shared by tools and the agent runtime."""

from .action import ActionReference, ActionType
from .error import ErrorDetail
from .execution import ContextResolution, ExecutionPlan, ExecutionStep
from .conversation import (
    ConversationHistoryTurn,
    ConversationTurnRole,
    FollowUpCandidate,
    FollowUpMode,
    FollowUpResolution,
)
from .fallback import FailedStepSummary, FallbackDirective, FallbackMode
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
from .validated_response import ValidatedResponse
from .result import ToolResult
from .source import SourceReference, SourceType
from .status import ResultStatus
from .tool_execution import (
    PlanExecutionResult,
    StepExecutionState,
    ToolStepExecution,
)
from .query_rewrite import (
    AppliedQueryContext,
    QueryRewriteProposal,
    QueryTarget,
    RewrittenQuery,
)

__all__ = [
    "ActionReference",
    "ActionType",
    "AppliedQueryContext",
    "AgentResponse",
    "Capability",
    "ContextField",
    "ConversationHistoryTurn",
    "ConversationTurnRole",
    "ContextNeed",
    "ContextSource",
    "ContextResolution",
    "ContextItem",
    "ContextOmission",
    "ErrorDetail",
    "FailedStepSummary",
    "ExecutionPlan",
    "ExecutionStep",
    "FallbackDirective",
    "FallbackMode",
    "FollowUpCandidate",
    "FollowUpMode",
    "FollowUpResolution",
    "ResultMeta",
    "ResultStatus",
    "ResponseContext",
    "ResponseDraft",
    "ValidatedResponse",
    "PlanExecutionResult",
    "StepExecutionState",
    "ToolStepExecution",
    "IntentType",
    "QuestionAnalysis",
    "QueryRewriteProposal",
    "QueryTarget",
    "RewrittenQuery",
    "SourceReference",
    "SourceType",
    "ToolResult",
]
