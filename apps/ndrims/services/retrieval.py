from __future__ import annotations

from typing import Protocol

from pgvector.django import CosineDistance
from pydantic import BaseModel, ConfigDict

from apps.ndrims.models import NdrimsMenu


class QueryEmbedder(Protocol):
    def embed_query(self, query: str) -> list[float]: ...


class RetrievedMenu(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    menu_key: str
    title: str
    breadcrumb: list[str]
    score: float
    source_url: str
    external_menu_id: str | None = None


class NdrimsMenuRetriever:
    def __init__(self, embedder: QueryEmbedder, *, minimum_score: float = 0.55):
        self.embedder = embedder
        self.minimum_score = minimum_score

    def search(self, query: str, *, top_k: int = 5) -> list[RetrievedMenu]:
        if not query.strip():
            raise ValueError("query must not be blank")
        if not 1 <= top_k <= 5:
            raise ValueError("top_k must be between 1 and 5")
        vector = self.embedder.embed_query(query)
        records = (
            NdrimsMenu.objects.filter(is_active=True, embedding__isnull=False)
            .select_related("parent")
            .annotate(distance=CosineDistance("embedding", vector))
            .order_by("distance", "menu_key")[:top_k]
        )
        return [
            RetrievedMenu(
                menu_key=menu.menu_key,
                title=menu.title,
                breadcrumb=menu.breadcrumb,
                score=1.0 - float(menu.distance),
                source_url=menu.source_url,
                external_menu_id=menu.external_menu_id or None,
            )
            for menu in records
            if 1.0 - float(menu.distance) >= self.minimum_score
        ]
