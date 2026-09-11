"""Deterministic hybrid retrieval using reciprocal-rank fusion (RRF)."""

from __future__ import annotations

from datetime import date
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field

from .fts import KeywordResult, KeywordRetriever
from .retrieval import DenseRetriever, RetrievedChunk


class HybridResult(BaseModel):
    """A citation-ready result with transparent per-retriever ranks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    rrf_score: float
    dense_rank: int | None = None
    keyword_rank: int | None = None
    source_id: str
    document_title: str
    canonical_url: str
    effective_year: int | None
    document_status: str
    heading_path: list[str]
    page_start: int | None = None
    page_end: int | None = None
    content: str


class HybridSearchResponse(BaseModel):
    """Hybrid results and local timing, without any extra LLM reranking call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    results: list[HybridResult]
    dense_duration_ms: int = Field(ge=0)
    keyword_duration_ms: int = Field(ge=0)
    fusion_duration_ms: int = Field(ge=0)


class HybridRetriever:
    """Fuse dense and exact-keyword ranks without comparing incompatible scores."""

    default_top_k = 5
    candidate_top_k = 10
    rrf_k = 60

    def __init__(self, dense_retriever: DenseRetriever, keyword_retriever: KeywordRetriever | None = None) -> None:
        self.dense_retriever = dense_retriever
        self.keyword_retriever = keyword_retriever or KeywordRetriever()

    def search(
        self,
        query: str,
        *,
        top_k: int = default_top_k,
        effective_year: int | None = None,
        document_status: str | None = None,
        effective_on: date | None = None,
        category: str | None = None,
    ) -> HybridSearchResponse:
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")

        dense_started = perf_counter()
        dense_results = self.dense_retriever.search(
            query,
            top_k=self.candidate_top_k,
            effective_year=effective_year,
            document_status=document_status,
            effective_on=effective_on,
            category=category,
        )
        dense_duration_ms = round((perf_counter() - dense_started) * 1000)

        keyword_started = perf_counter()
        keyword_results = self.keyword_retriever.search(
            query,
            top_k=self.candidate_top_k,
            effective_year=effective_year,
            document_status=document_status,
            effective_on=effective_on,
            category=category,
        )
        keyword_duration_ms = round((perf_counter() - keyword_started) * 1000)

        fusion_started = perf_counter()
        fused = self._fuse(dense_results, keyword_results)
        fusion_duration_ms = round((perf_counter() - fusion_started) * 1000)
        return HybridSearchResponse(
            results=fused[:top_k],
            dense_duration_ms=dense_duration_ms,
            keyword_duration_ms=keyword_duration_ms,
            fusion_duration_ms=fusion_duration_ms,
        )

    def _fuse(self, dense_results: list[RetrievedChunk], keyword_results: list[KeywordResult]) -> list[HybridResult]:
        candidates: dict[str, dict[str, object]] = {}

        for rank, result in enumerate(dense_results, start=1):
            candidate = candidates.setdefault(result.chunk_id, {"dense": None, "keyword": None})
            candidate["dense"] = (rank, result)
        for rank, result in enumerate(keyword_results, start=1):
            candidate = candidates.setdefault(result.chunk_id, {"dense": None, "keyword": None})
            candidate["keyword"] = (rank, result)

        fused: list[HybridResult] = []
        for chunk_id, candidate in candidates.items():
            dense_entry = candidate["dense"]
            keyword_entry = candidate["keyword"]
            dense_rank = dense_entry[0] if dense_entry else None
            keyword_rank = keyword_entry[0] if keyword_entry else None
            score = sum(1 / (self.rrf_k + rank) for rank in (dense_rank, keyword_rank) if rank is not None)
            source = dense_entry[1] if dense_entry else keyword_entry[1]
            fused.append(
                HybridResult(
                    chunk_id=chunk_id,
                    rrf_score=score,
                    dense_rank=dense_rank,
                    keyword_rank=keyword_rank,
                    source_id=source.source_id,
                    document_title=source.document_title,
                    canonical_url=source.canonical_url,
                    effective_year=source.effective_year,
                    document_status=source.document_status,
                    heading_path=source.heading_path,
                    page_start=getattr(source, "page_start", None),
                    page_end=getattr(source, "page_end", None),
                    content=source.content,
                )
            )
        return sorted(fused, key=lambda item: (-item.rrf_score, item.chunk_id))
