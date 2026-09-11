from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, HttpUrl, model_validator

from .base import ContractModel


class ActionType(StrEnum):
    OPEN_URL = "open_url"
    NAVIGATE_NDRIMS_MENU = "navigate_ndrims_menu"
    REQUEST_CONFIRMATION = "request_confirmation"


class ActionReference(ContractModel):
    """A server-registered action; never an LLM-invented destination."""

    action_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]*$")]
    action_type: ActionType
    label: Annotated[str, Field(min_length=1, max_length=100)]
    url: HttpUrl | None = None
    requires_confirmation: bool = False

    @model_validator(mode="after")
    def validate_action_contract(self) -> Self:
        if self.action_type == ActionType.OPEN_URL and self.url is None:
            raise ValueError("open_url actions require a validated URL")
        if self.action_type == ActionType.NAVIGATE_NDRIMS_MENU and self.url is not None:
            raise ValueError("nDRIMS menu actions use a registered menu ID, not an LLM-generated URL")
        if self.action_type == ActionType.REQUEST_CONFIRMATION:
            object.__setattr__(self, "requires_confirmation", True)
        return self
