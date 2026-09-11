"""Dense cosine retrieval over official university knowledge chunks."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from pgvector.django import CosineDistance
from django.db.models import Q
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
    document_status: str
    effective_from: date | None
    effective_to: date | None
    heading_path: list[str]
    page_start: int | None
    page_end: int | None
    content: str


class DenseRetriever:
    default_top_k = 5
    maximum_top_k = 20

    def __init__(self, embedder: QueryEmbedder) -> None:
        self.embedder = embedder

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        effective_year: int | None = None,
        document_status: str | None = None,
        effective_on: date | None = None,
        category: str | None = None,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            raise ValueError("query must not be blank")
        limit = top_k or self.default_top_k
        if not 1 <= limit <= self.maximum_top_k:
            raise ValueError(f"top_k must be between 1 and {self.maximum_top_k}")

        query_vector = self.embedder.embed_query(query)
        filters = Q(embedding__isnull=False)
        if effective_year is not None:
            filters &= Q(document__effective_year=effective_year)
        if document_status is not None:
            filters &= Q(document__document_status=document_status)
        if category is not None:
            filters &= Q(document__category__contains=[category])
        if effective_on is not None:
            filters &= (Q(document__effective_from__isnull=True) | Q(document__effective_from__lte=effective_on))
            filters &= (Q(document__effective_to__isnull=True) | Q(document__effective_to__gte=effective_on))

        records = (
            KnowledgeChunk.objects.filter(filters)
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
                document_status=record.document.document_status,
                effective_from=record.document.effective_from,
                effective_to=record.document.effective_to,
                heading_path=record.heading_path,
                page_start=record.page_start,
                page_end=record.page_end,
                content=record.content,
            )
            for record in records
        ]
