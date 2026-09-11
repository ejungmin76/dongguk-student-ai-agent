from datetime import date

from pydantic import Field

from agent.schemas.base import ContractModel


class UniversityKnowledgeSearchInput(ContractModel):
    """Facts supplied by the future planner; no service-category vocabulary is required."""

    question: str = Field(min_length=2, max_length=1_000)
    effective_year: int | None = None
    effective_on: date | None = None
    top_k: int = Field(default=5, ge=1, le=5)


class UniversityKnowledgeSearchHit(ContractModel):
    chunk_id: str
    content: str
    heading_path: list[str]
    rrf_score: float
    dense_rank: int | None = None
    keyword_rank: int | None = None
    source_id: str
    document_title: str
    canonical_url: str
    effective_year: int | None = None
    document_status: str
    effective_from: date | None = None
    effective_to: date | None = None
    page_start: int | None = None
    page_end: int | None = None


class UniversityKnowledgeSearchData(ContractModel):
    """Evidence the response agent may summarize, but must not treat as an answer by itself."""

    results: list[UniversityKnowledgeSearchHit] = Field(min_length=1, max_length=5)
    dense_duration_ms: int = Field(ge=0)
    keyword_duration_ms: int = Field(ge=0)
    fusion_duration_ms: int = Field(ge=0)
