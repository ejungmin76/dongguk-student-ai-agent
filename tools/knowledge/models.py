"""Normalized document models for the university knowledge ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeSource:
    """One public source declared in the source catalog."""

    source_id: str
    title: str
    url: str
    source_type: str
    category: list[str]
    priority: str
    enabled: bool
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DownloadedSource:
    """The locally persisted original response."""

    source: KnowledgeSource
    content: bytes
    content_type: str
    fetched_at: str
    content_hash: str
    raw_path: Path


@dataclass(frozen=True)
class NormalizedDocument:
    """Search-ready text with provenance retained outside the text body."""

    source: KnowledgeSource
    title: str
    content: str
    source_type: str
    page_count: int | None
    content_hash: str
    fetched_at: str
    raw_path: Path
