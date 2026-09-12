from typing import Any

from pydantic import Field

from .action import ActionReference
from .base import ContractModel
from .error import ErrorDetail
from .planning import Capability
from .source import SourceReference
from .status import ResultStatus


class ContextItem(ContractModel):
    """Sanitized facts from one executed capability."""

    step_id: str
    capability: Capability
    data: dict[str, Any]


class ContextOmission(ContractModel):
    """A transparent record of data removed to meet the response budget."""

    path: str
    reason: str
    count: int = Field(ge=1)


class ResponseContext(ContractModel):
    """Minimal, citable context passed to the future Response Agent."""

    status: ResultStatus
    items: list[ContextItem] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    actions: list[ActionReference] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)
    token_budget: int = Field(ge=256)
    estimated_tokens: int = Field(ge=0)
    truncated: bool = False
    omissions: list[ContextOmission] = Field(default_factory=list)

