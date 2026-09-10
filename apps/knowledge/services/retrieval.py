"""Dense cosine retrieval over official university knowledge chunks."""

from __future__ import annotations

from typing import Protocol

from pgvector.django import CosineDistance
from pydantic import BaseModel, ConfigDict, Field

from ..models import KnowledgeChunk


class QueryEmbedder(Protocol):
    model_name: str
    dimensions: int

    def embed_query(self, query: str) -> list[float]: ...


class RetrievedChunk(BaseModel):
    """One citation-ready dense retrieval result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    score: float
    source_id: str
    document_title: str
    canonical_url: str
    effective_year: int | None
    heading_path: list[str]
    page_start: int | None
    page_end: int | None
    content: str


class DenseRetriever:
    default_top_k = 5
    maximum_top_k = 20

    def __init__(self, embedder: QueryEmbedder) -> None:
        self.embedder = embedder

    def search(self, query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        if not query.strip():
            raise ValueError("query must not be blank")
        limit = top_k or self.default_top_k
        if not 1 <= limit <= self.maximum_top_k:
            raise ValueError(f"top_k must be between 1 and {self.maximum_top_k}")

        query_vector = self.embedder.embed_query(query)
        records = (
            KnowledgeChunk.objects.filter(embedding__isnull=False)
            .select_related("document")
            .annotate(distance=CosineDistance("embedding", query_vector))
            .order_by("distance", "chunk_id")[:limit]
        )
        return [
            RetrievedChunk(
                chunk_id=record.chunk_id,
                score=1.0 - float(record.distance),
                source_id=record.document.source_id,
                document_title=record.document.title,
                canonical_url=record.document.canonical_url,
                effective_year=record.document.effective_year,
                heading_path=record.heading_path,
                page_start=record.page_start,
                page_end=record.page_end,
                content=record.content,
            )
            for record in records
        ]
