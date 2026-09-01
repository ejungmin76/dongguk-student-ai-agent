from typing import Generic, Self, TypeVar

from pydantic import BaseModel, Field, model_validator

from .action import ActionReference
from .base import ContractModel
from .error import ErrorDetail
from .meta import ResultMeta
from .source import SourceReference
from .status import ResultStatus

DataT = TypeVar("DataT", bound=BaseModel)


class ToolResult(ContractModel, Generic[DataT]):
    """Common envelope around a tool-specific Pydantic data model."""

    status: ResultStatus
    data: DataT | None = None
    sources: list[SourceReference] = Field(default_factory=list)
    actions: list[ActionReference] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)
    meta: ResultMeta

    @model_validator(mode="after")
    def validate_status_contract(self) -> Self:
        if self.status == ResultStatus.SUCCESS:
            if self.data is None:
                raise ValueError("success results require data")
            if self.errors:
                raise ValueError("success results cannot contain errors")

        elif self.status == ResultStatus.PARTIAL:
            if self.data is None or not self.errors:
                raise ValueError("partial results require both data and errors")

        elif self.status == ResultStatus.CLARIFICATION:
            if not self.errors:
                raise ValueError("clarification results require a reason")

        elif self.status == ResultStatus.UNAVAILABLE:
            if self.data is not None:
                raise ValueError("unavailable results cannot contain data")
            if not self.errors:
                raise ValueError("unavailable results require an error")

        return self
