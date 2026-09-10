"""Section-aware chunks and provenance metadata for university documents."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
PAGE_MARKER_RE = re.compile(r"^<!--\s*page:\s*(\d+)\s*-->\s*$", re.IGNORECASE)


class ChunkingConfig(BaseModel):
    """Deliberate PoC defaults; the experiment record explains their choice."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_chars: int = Field(default=1200, ge=300, le=4000)
    overlap_chars: int = Field(default=150, ge=0, le=1000)

    @model_validator(mode="after")
    def overlap_must_be_smaller_than_chunk(self) -> "ChunkingConfig":
        if self.overlap_chars >= self.max_chars:
            raise ValueError("overlap_chars must be smaller than max_chars")
        return self


class KnowledgeChunk(BaseModel):
    """One retrievable document passage with enough context for a citation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    document_title: str = Field(min_length=1)
    canonical_url: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    category: list[str]
    effective_year: int | None = Field(default=None, ge=1900, le=3000)
    fetched_at: str | None = None
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    heading_path: list[str]
    section_ordinal: int = Field(ge=0)
    chunk_ordinal: int = Field(ge=0)
    content: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)

    @model_validator(mode="after")
    def page_range_must_be_valid(self) -> "KnowledgeChunk":
        if self.page_start and self.page_end and self.page_start > self.page_end:
            raise ValueError("page_start must not be later than page_end")
        return self


class _Section(BaseModel):
    model_config = ConfigDict(frozen=True)

    heading_path: list[str]
    content: str
    page_start: int | None
    page_end: int | None


def _split_front_matter(markdown: str) -> tuple[dict[str, object], str]:
    if not markdown.startswith("---\n"):
        raise ValueError("Cleaned document must begin with YAML front matter.")
    _, front_matter, body = markdown.split("---\n", 2)
    metadata = yaml.safe_load(front_matter)
    if not isinstance(metadata, dict):
        raise ValueError("Document front matter must be a mapping.")
    return metadata, body.strip()


def _sections(body: str, document_title: str) -> list[_Section]:
    """Split Markdown by headings while retaining a full heading path."""

    sections: list[_Section] = []
    heading_stack: list[tuple[int, str]] = []
    content_lines: list[str] = []
    current_page: int | None = None
    section_page_start: int | None = None

    def flush() -> None:
        nonlocal content_lines, section_page_start
        content = "\n".join(content_lines).strip()
        if content:
            sections.append(
                _Section(
                    heading_path=[title for _, title in heading_stack] or [document_title],
                    content=content,
                    page_start=section_page_start,
                    page_end=current_page,
                )
            )
        content_lines = []
        section_page_start = current_page

    for line in body.splitlines():
        marker = PAGE_MARKER_RE.match(line)
        if marker:
            current_page = int(marker.group(1))
            if section_page_start is None:
                section_page_start = current_page
            continue
        heading = HEADING_RE.match(line)
        if heading:
            flush()
            level, title = len(heading.group(1)), heading.group(2)
            heading_stack = [(old_level, old_title) for old_level, old_title in heading_stack if old_level < level]
            heading_stack.append((level, title))
            continue
        content_lines.append(line)
    flush()
    return sections


def _tail(text: str, max_chars: int) -> str:
    if max_chars == 0:
        return ""
    tail = text[-max_chars:].strip()
    first_space = tail.find(" ")
    return tail[first_space + 1 :] if first_space >= 0 else tail


def _split_large_block(block: str, max_chars: int) -> list[str]:
    if len(block) <= max_chars:
        return [block]
    sentences = re.split(r"(?<=[.!?다])\s+", block)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def _window_section(content: str, config: ChunkingConfig) -> list[str]:
    """Keep paragraphs/table blocks intact whenever possible and add tail overlap."""

    blocks = [block.strip() for block in re.split(r"\n{2,}", content) if block.strip()]
    pieces = [piece for block in blocks for piece in _split_large_block(block, config.max_chars)]
    windows: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current}\n\n{piece}".strip() if current else piece
        if current and len(candidate) > config.max_chars:
            windows.append(current)
            overlap = _tail(current, config.overlap_chars)
            current = f"{overlap}\n\n{piece}".strip() if overlap else piece
        else:
            current = candidate
    if current:
        windows.append(current)
    return windows


def chunk_markdown(markdown: str, config: ChunkingConfig | None = None) -> list[KnowledgeChunk]:
    """Turn cleaned Markdown into stable, section-aware retrieval chunks."""

    config = config or ChunkingConfig()
    metadata, body = _split_front_matter(markdown)
    source_id = str(metadata["source_id"])
    # A few public pages expose no useful HTML title. Preserve a non-empty
    # retrieval label until their catalog title can be improved upstream.
    title = str(metadata.get("title") or source_id)
    chunks: list[KnowledgeChunk] = []
    for section_ordinal, section in enumerate(_sections(body, title)):
        for chunk_ordinal, content in enumerate(_window_section(section.content, config)):
            digest = hashlib.sha256(f"{source_id}|{section_ordinal}|{chunk_ordinal}|{content}".encode()).hexdigest()
            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"{source_id}:{section_ordinal}:{chunk_ordinal}:{digest[:12]}",
                    source_id=source_id,
                    document_title=title,
                    canonical_url=str(metadata.get("canonical_url") or "unknown://source"),
                    source_type=str(metadata.get("source_type") or "unknown"),
                    category=[str(item) for item in metadata.get("category", [])],
                    effective_year=metadata.get("effective_year"),
                    fetched_at=metadata.get("fetched_at"),
                    page_start=section.page_start,
                    page_end=section.page_end,
                    heading_path=section.heading_path,
                    section_ordinal=section_ordinal,
                    chunk_ordinal=chunk_ordinal,
                    content=content,
                    content_hash=str(metadata.get("content_hash") or hashlib.sha256(body.encode()).hexdigest()),
                )
            )
    return chunks


def chunk_cleaned_directory(input_dir: Path, output_path: Path, config: ChunkingConfig | None = None) -> list[KnowledgeChunk]:
    """Chunk all cleaned Markdown files into one JSONL artifact outside Git."""

    chunks: list[KnowledgeChunk] = []
    for path in sorted(input_dir.glob("*.md")):
        chunks.extend(chunk_markdown(path.read_text(encoding="utf-8"), config))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(chunk.model_dump_json() + "\n" for chunk in chunks), encoding="utf-8")
    return chunks
