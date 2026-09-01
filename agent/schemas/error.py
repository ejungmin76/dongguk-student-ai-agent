from typing import Annotated

from pydantic import Field

from .base import ContractModel

ErrorCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]*$")]


class ErrorDetail(ContractModel):
    """Stable machine code plus a safe user-facing explanation."""

    code: ErrorCode
    message: Annotated[str, Field(min_length=1, max_length=500)]
    retryable: bool = False
