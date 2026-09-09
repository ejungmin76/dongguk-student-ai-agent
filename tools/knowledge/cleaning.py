"""Format-preserving cleaning helpers for public university documents."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable


WHITESPACE_RE = re.compile(r"[ \t]+")
BLANK_LINES_RE = re.compile(r"\n{3,}")


def normalize_line(line: str) -> str:
    """Keep Korean and Markdown characters while making spacing predictable."""

    return WHITESPACE_RE.sub(" ", line.replace("\u00a0", " ")).strip()


def clean_text(text: str) -> str:
    """Remove blank noise and adjacent duplicate lines without flattening lists/tables."""

    lines: list[str] = []
    previous = None
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = normalize_line(raw_line)
        if line and line == previous:
            continue
        lines.append(line)
        previous = line if line else None

    return BLANK_LINES_RE.sub("\n\n", "\n".join(lines)).strip()


def deduplicate_blocks(blocks: Iterable[str]) -> list[str]:
    """Keep the first occurrence of an identical HTML content block.

    University pages frequently repeat their notice summary in a print/mobile
    section. Blocks (rather than individual words) are compared, so tables and
    Korean sentences keep their original structure.
    """

    seen: set[str] = set()
    result: list[str] = []
    for block in blocks:
        normalized = clean_text(block)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def repeated_page_margin_lines(pages: Iterable[str], *, minimum_ratio: float = 0.6) -> set[str]:
    """Find repeated first/last text lines, usually PDF headers and footers.

    A line must occur at the top or bottom of at least 60% of pages. This avoids
    deleting a normal sentence which happens to occur inside the document.
    """

    page_list = list(pages)
    if len(page_list) < 2:
        return set()

    candidates: list[str] = []
    for page in page_list:
        lines = [normalize_line(line) for line in page.splitlines()]
        lines = [line for line in lines if line]
        candidates.extend(lines[:2])
        candidates.extend(lines[-2:])

    threshold = max(2, int(len(page_list) * minimum_ratio + 0.999))
    return {line for line, count in Counter(candidates).items() if count >= threshold}


def clean_pdf_pages(pages: Iterable[str]) -> str:
    """Join extracted PDF pages after removing repeated page margins."""

    page_list = list(pages)
    margins = repeated_page_margin_lines(page_list)
    cleaned_pages: list[str] = []

    for page in page_list:
        kept_lines = [line for line in page.splitlines() if normalize_line(line) not in margins]
        cleaned_pages.append("\n".join(kept_lines))

    return clean_text("\n\n".join(cleaned_pages))
