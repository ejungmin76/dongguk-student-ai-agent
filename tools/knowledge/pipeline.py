"""Download, parse, clean, and persist public university knowledge sources."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml
from bs4 import BeautifulSoup, Tag
import pymupdf
from pypdf import PdfReader

from .cleaning import clean_pdf_pages, clean_text, deduplicate_blocks
from .models import DownloadedSource, KnowledgeSource, NormalizedDocument


USER_AGENT = "dongguk-student-ai-agent/0.1 (+educational-poc; public-document-ingestion)"
HTML_NOISE_TAGS = {"script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg"}


class KnowledgeIngestionError(RuntimeError):
    """Raised when a source cannot be downloaded or normalized."""


def load_catalog(catalog_path: Path, *, enabled_only: bool = True) -> list[KnowledgeSource]:
    """Load the committed catalog without accepting arbitrary YAML object tags."""

    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise KnowledgeIngestionError("Catalog must contain a 'sources' list.")

    sources: list[KnowledgeSource] = []
    for item in payload["sources"]:
        if not isinstance(item, dict):
            raise KnowledgeIngestionError("Each catalog source must be a mapping.")
        enabled = bool(item.get("enabled", False))
        if enabled_only and not enabled:
            continue
        try:
            sources.append(
                KnowledgeSource(
                    source_id=str(item["id"]),
                    title=str(item["title"]),
                    url=str(item["url"]),
                    source_type=str(item["type"]),
                    category=list(item.get("category", [])),
                    priority=str(item["priority"]),
                    enabled=enabled,
                    metadata={
                        key: value
                        for key, value in item.items()
                        if key
                        not in {"id", "title", "url", "type", "category", "priority", "enabled"}
                    },
                )
            )
        except KeyError as error:
            raise KnowledgeIngestionError(f"Catalog source is missing {error.args[0]!r}.") from error
    return sources


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _extension_for(source: KnowledgeSource, content_type: str) -> str:
    if "pdf" in content_type.lower() or source.source_type == "pdf":
        return ".pdf"
    if "html" in content_type.lower() or source.source_type.startswith("html"):
        return ".html"
    guessed = mimetypes.guess_extension(content_type.partition(";")[0].strip())
    return guessed or ".bin"


class KnowledgePipeline:
    """Filesystem-backed pipeline; generated data is deliberately outside Git."""

    def __init__(
        self,
        *,
        output_dir: Path,
        timeout_seconds: int = 30,
        request_interval_seconds: float = 3,
    ) -> None:
        self.output_dir = output_dir
        self.timeout_seconds = timeout_seconds
        self.request_interval_seconds = request_interval_seconds
        self.raw_dir = output_dir / "raw"
        self.parsed_dir = output_dir / "parsed"
        self.cleaned_dir = output_dir / "cleaned"
        self.manifest_dir = output_dir / "manifests"

    def prepare_output_dirs(self) -> None:
        for directory in (self.raw_dir, self.parsed_dir, self.cleaned_dir, self.manifest_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def download(self, source: KnowledgeSource) -> DownloadedSource:
        """Download one unauthenticated public source and persist its exact response."""

        self.prepare_output_dirs()
        request = Request(source.url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - URLs are curated in catalog
                content = response.read()
                content_type = response.headers.get_content_type() or "application/octet-stream"
        except (HTTPError, URLError, TimeoutError) as error:
            raise KnowledgeIngestionError(f"Download failed for {source.source_id}: {error}") from error

        content_hash = hashlib.sha256(content).hexdigest()
        raw_path = self.raw_dir / f"{source.source_id}{_extension_for(source, content_type)}"
        raw_path.write_bytes(content)
        return DownloadedSource(
            source=source,
            content=content,
            content_type=content_type,
            fetched_at=_utc_now(),
            content_hash=content_hash,
            raw_path=raw_path,
        )

    def normalize(self, downloaded: DownloadedSource) -> NormalizedDocument:
        """Parse HTML/PDF into clean text and retain source metadata."""

        if "pdf" in downloaded.content_type.lower() or downloaded.source.source_type == "pdf":
            title, content, page_count = self._parse_pdf(downloaded)
            source_type = "pdf"
        else:
            title, content = self._parse_html(downloaded)
            page_count = None
            source_type = "html"

        if not content:
            raise KnowledgeIngestionError(f"No readable text extracted from {downloaded.source.source_id}.")
        return NormalizedDocument(
            source=downloaded.source,
            title=title,
            content=content,
            source_type=source_type,
            page_count=page_count,
            content_hash=downloaded.content_hash,
            fetched_at=downloaded.fetched_at,
            raw_path=downloaded.raw_path,
        )

    def persist(self, document: NormalizedDocument) -> Path:
        """Persist parsed JSON, cleaned Markdown, and a provenance manifest."""

        self.prepare_output_dirs()
        parsed_path = self.parsed_dir / f"{document.source.source_id}.json"
        cleaned_path = self.cleaned_dir / f"{document.source.source_id}.md"
        manifest_path = self.manifest_dir / f"{document.source.source_id}.json"

        parsed_payload = {"title": document.title, "content": document.content, "page_count": document.page_count}
        parsed_path.write_text(json.dumps(parsed_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        front_matter = {
            "source_id": document.source.source_id,
            "title": document.title,
            "canonical_url": document.source.url,
            "publisher": document.source.metadata.get("publisher", ""),
            "source_type": document.source_type,
            "category": document.source.category,
            "priority": document.source.priority,
            "effective_year": document.source.metadata.get("effective_year"),
            "fetched_at": document.fetched_at,
            "content_hash": document.content_hash,
            "page_count": document.page_count,
        }
        cleaned_path.write_text(
            "---\n" + yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False) + "---\n\n" + document.content + "\n",
            encoding="utf-8",
        )
        manifest_path.write_text(
            json.dumps(
                {
                    **front_matter,
                    "raw_path": str(document.raw_path),
                    "parsed_path": str(parsed_path),
                    "cleaned_path": str(cleaned_path),
                    "status": "success",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return cleaned_path

    def ingest(self, source: KnowledgeSource) -> Path:
        """Download, normalize, and persist one source."""

        downloaded = self.download(source)
        document = self.normalize(downloaded)
        return self.persist(document)

    def ingest_all(self, sources: list[KnowledgeSource]) -> dict[str, Path | Exception]:
        """Process catalog sources sequentially to respect conservative request limits."""

        results: dict[str, Path | Exception] = {}
        for index, source in enumerate(sources):
            try:
                results[source.source_id] = self.ingest(source)
            except Exception as error:  # Keep batch ingestion useful when one source changes.
                results[source.source_id] = error
            if index < len(sources) - 1 and self.request_interval_seconds:
                time.sleep(self.request_interval_seconds)
        return results

    @staticmethod
    def _parse_html(downloaded: DownloadedSource) -> tuple[str, str]:
        # The university sites send UTF-8 pages but some omit or misstate the
        # charset header. Decoding explicitly prevents Korean mojibake.
        soup = BeautifulSoup(downloaded.content.decode("utf-8", errors="replace"), "html.parser")
        for tag in soup.find_all(HTML_NOISE_TAGS):
            tag.decompose()

        root = (
            soup.select_one("#contents > .contents")
            or soup.select_one("#contents .contents")
            or soup.find("main")
            or soup.find("article")
            or soup.find(id="content")
            or soup.body
            or soup
        )
        title_tag = root.find("h1") if isinstance(root, Tag) else None
        title = clean_text(title_tag.get_text(" ", strip=True) if title_tag else downloaded.source.title)
        blocks: list[str] = []

        for element in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "table"]):
            if element.name == "table":
                table = KnowledgePipeline._table_to_markdown(element)
                if table:
                    blocks.append(table)
                continue
            text = clean_text(element.get_text(" ", strip=True))
            if not text:
                continue
            if element.name and element.name.startswith("h"):
                level = min(int(element.name[1]), 4)
                blocks.append(f"{'#' * level} {text}")
            elif element.name == "li":
                blocks.append(f"- {text}")
            else:
                blocks.append(text)

        return title, clean_text("\n\n".join(deduplicate_blocks(blocks)))

    @staticmethod
    def _table_to_markdown(table: Tag) -> str:
        rows: list[list[str]] = []
        for row in table.find_all("tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)).replace("|", "\\|") for cell in row.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if not rows:
            return ""

        width = max(len(row) for row in rows)
        normalized = [row + [""] * (width - len(row)) for row in rows]
        header = normalized[0]
        return "\n".join(
            [
                "| " + " | ".join(header) + " |",
                "| " + " | ".join(["---"] * width) + " |",
                *["| " + " | ".join(row) + " |" for row in normalized[1:]],
            ]
        )

    @staticmethod
    def _parse_pdf(downloaded: DownloadedSource) -> tuple[str, str, int]:
        # PyMuPDF has substantially better CMap support for Korean public PDFs.
        # pypdf remains as a lightweight fallback for malformed documents.
        try:
            pdf = pymupdf.open(stream=downloaded.content, filetype="pdf")
            pages = [page.get_text("text") or "" for page in pdf]
            metadata_title = (pdf.metadata or {}).get("title") or downloaded.source.title
            if any(page.strip() for page in pages):
                return clean_text(str(metadata_title)), clean_pdf_pages(pages), len(pages)
        except Exception:
            # The fallback below supplies a source-specific error when it fails.
            pass

        try:
            reader = PdfReader(BytesIO(downloaded.content))
            pages = [(page.extract_text(extraction_mode="layout") or "") for page in reader.pages]
            metadata_title = reader.metadata.title if reader.metadata and reader.metadata.title else downloaded.source.title
            return clean_text(str(metadata_title)), clean_pdf_pages(pages), len(pages)
        except Exception as error:
            raise KnowledgeIngestionError(f"Invalid PDF for {downloaded.source.source_id}: {error}") from error
