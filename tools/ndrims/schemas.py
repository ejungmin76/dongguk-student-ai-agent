from typing import Literal

from pydantic import Field

from agent.schemas.base import ContractModel


class NdrimsMenuSearchInput(ContractModel):
    question: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=5)


class NdrimsMenuCandidate(ContractModel):
    menu_key: str
    title: str
    breadcrumb: list[str] = Field(min_length=1)
    score: float = Field(ge=-1, le=1)
    source_url: str
    external_menu_id: str | None = None
    navigation_state: Literal["requires_extension_validation"] = "requires_extension_validation"


class NdrimsMenuSearchData(ContractModel):
    candidates: list[NdrimsMenuCandidate] = Field(min_length=1, max_length=5)
    requires_user_selection: bool
