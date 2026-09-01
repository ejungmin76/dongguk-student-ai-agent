from typing import Annotated

from pydantic import Field, NonNegativeInt

from .base import ContractModel


class ResultMeta(ContractModel):
    tool_name: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
    execution_id: Annotated[str, Field(min_length=1, max_length=100)]
    duration_ms: NonNegativeInt | None = None
