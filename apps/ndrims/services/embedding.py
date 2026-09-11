from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from django.utils.timezone import now

from apps.ndrims.models import NdrimsMenu


class MenuEmbedder(Protocol):
    model_name: str
    dimensions: int

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


@dataclass(frozen=True)
class MenuEmbeddingResult:
    embedded: int
    skipped: int


def menu_search_text(menu: NdrimsMenu) -> str:
    path = " > ".join(menu.breadcrumb)
    return f"nDRIMS student menu\npath: {path}\nmenu: {menu.title}"


def index_menu_embeddings(embedder: MenuEmbedder, *, batch_size: int = 50) -> MenuEmbeddingResult:
    pending: list[tuple[NdrimsMenu, str, str]] = []
    skipped = 0
    for menu in NdrimsMenu.objects.select_related("parent").filter(is_active=True):
        text = menu_search_text(menu)
        source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if menu.embedding is not None and menu.embedding_model == embedder.model_name and menu.embedding_source_hash == source_hash:
            skipped += 1
        else:
            pending.append((menu, text, source_hash))

    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        vectors = embedder.embed_texts([text for _, text, _ in batch])
        for (menu, _, source_hash), vector in zip(batch, vectors, strict=True):
            menu.embedding = vector
            menu.embedding_model = embedder.model_name
            menu.embedding_source_hash = source_hash
            menu.embedded_at = now()
            menu.save(update_fields=["embedding", "embedding_model", "embedding_source_hash", "embedded_at", "updated_at"])
    return MenuEmbeddingResult(embedded=len(pending), skipped=skipped)
