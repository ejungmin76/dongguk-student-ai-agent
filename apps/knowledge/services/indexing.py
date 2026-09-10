"""Idempotent persistence of cleaned RAG chunks and their embeddings."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now

from tools.knowledge.chunking import KnowledgeChunk as ChunkPayload

from ..models import KnowledgeChunk, KnowledgeDocument
from .embedding import DocumentEmbedder


@dataclass(frozen=True)
class IndexingResult:
    documents: int
    created_chunks: int
    updated_chunks: int
    deleted_chunks: int
    embedded_chunks: int
    skipped_embeddings: int


def load_chunks(path: Path) -> list[ChunkPayload]:
    """Load the local-only JSONL emitted by the chunking command."""

    if not path.is_file():
        raise FileNotFoundError(f"Chunk file not found: {path}")
    return [ChunkPayload.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _chunk_text_hash(chunk: ChunkPayload) -> str:
    return hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()


def _parsed_timestamp(value: str | None) -> datetime | None:
    return parse_datetime(value) if value else None


def index_chunks(chunks: Iterable[ChunkPayload], *, embedder: DocumentEmbedder | None = None, batch_size: int = 20) -> IndexingResult:
    """Upsert chunks, embedding only new or changed content."""

    payloads = list(chunks)
    pending: list[tuple[KnowledgeChunk, ChunkPayload]] = []
    created = updated = deleted = skipped = 0
    documents: dict[str, KnowledgeDocument] = {}
    active_chunk_ids: dict[str, set[str]] = {}

    with transaction.atomic():
        for payload in payloads:
            active_chunk_ids.setdefault(payload.source_id, set()).add(payload.chunk_id)
            document = documents.get(payload.source_id)
            if document is None:
                document, _ = KnowledgeDocument.objects.update_or_create(
                    source_id=payload.source_id,
                    defaults={
                        "title": payload.document_title,
                        "canonical_url": payload.canonical_url,
                        "source_type": payload.source_type,
                        "category": payload.category,
                        "effective_year": payload.effective_year,
                        "fetched_at": _parsed_timestamp(payload.fetched_at),
                        "content_hash": payload.content_hash,
                    },
                )
                documents[payload.source_id] = document

            text_hash = _chunk_text_hash(payload)
            record, was_created = KnowledgeChunk.objects.get_or_create(
                chunk_id=payload.chunk_id,
                defaults={
                    "document": document,
                    "heading_path": payload.heading_path,
                    "section_ordinal": payload.section_ordinal,
                    "chunk_ordinal": payload.chunk_ordinal,
                    "page_start": payload.page_start,
                    "page_end": payload.page_end,
                    "content": payload.content,
                    "content_hash": text_hash,
                },
            )
            if was_created:
                created += 1
                if embedder:
                    pending.append((record, payload))
            elif record.content_hash != text_hash:
                record.document = document
                record.heading_path = payload.heading_path
                record.section_ordinal = payload.section_ordinal
                record.chunk_ordinal = payload.chunk_ordinal
                record.page_start = payload.page_start
                record.page_end = payload.page_end
                record.content = payload.content
                record.content_hash = text_hash
                record.embedding = None
                record.embedding_model = ""
                record.embedded_at = None
                record.save()
                updated += 1
                if embedder:
                    pending.append((record, payload))
            elif embedder and (record.embedding is None or record.embedding_model != embedder.model_name):
                # A prior --skip-embeddings run intentionally creates the row
                # without a vector. The next normal run must fill that gap.
                pending.append((record, payload))
            else:
                skipped += 1

        # Chunk settings can change an ID even when the original document has
        # not changed. Remove only stale chunks belonging to sources included
        # in this run, so old vectors never appear beside the current chunks.
        for source_id, document in documents.items():
            deleted += KnowledgeChunk.objects.filter(document=document).exclude(
                chunk_id__in=active_chunk_ids[source_id]
            ).delete()[0]

        if embedder:
            for start in range(0, len(pending), batch_size):
                batch = pending[start : start + batch_size]
                vectors = embedder.embed_documents([payload for _, payload in batch])
                for (record, _), vector in zip(batch, vectors, strict=True):
                    record.embedding = vector
                    record.embedding_model = embedder.model_name
                    record.embedded_at = now()
                    record.save(update_fields=["embedding", "embedding_model", "embedded_at", "updated_at"])

    return IndexingResult(
        documents=len(documents),
        created_chunks=created,
        updated_chunks=updated,
        deleted_chunks=deleted,
        embedded_chunks=len(pending) if embedder else 0,
        skipped_embeddings=skipped,
    )
