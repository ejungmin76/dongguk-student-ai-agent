"""Korean-safe PostgreSQL full-text search and metadata filtering."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Iterable

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, Value
from pydantic import BaseModel, ConfigDict

from ..models import KnowledgeChunk


# No Korean stop-word dictionary is used. It would make retrieval behavior
# depend on a hand-maintained list of expressions. These patterns only retain
# syntactically meaningful academic forms: ordinary terms, grade codes, and
# course codes.
TOKEN_RE = re.compile(
    r"[a-f][+-]|[a-f]0|[a-z]{2,}\d{3,}|[0-9a-z가-힣]{2,}",
    re.IGNORECASE,
)


def keyword_terms(query: str) -> list[str]:
    """Normalize Korean punctuation and retain meaningful exact terms only."""

    normalized = unicodedata.normalize("NFKC", query).lower().replace("·", " ")
    terms: list[str] = []
    for term in TOKEN_RE.findall(normalized):
        if term not in terms:
            terms.append(term)
    return terms


def search_text_for(chunk: KnowledgeChunk) -> str:
    document = chunk.document
    return "\n".join(
        [
            document.title,
            " ".join(chunk.heading_path),
            " ".join(document.category),
            str(document.effective_year or ""),
            chunk.content,
        ]
    )


def search_label_for(chunk: KnowledgeChunk) -> str:
    """Short official labels are a safe target for typo tolerance."""

    return " ".join([chunk.document.title, *chunk.heading_path])


def refresh_fts(chunks: Iterable[KnowledgeChunk]) -> int:
    """Build PostgreSQL's simple-config FTS vectors for exact Korean tokens."""

    count = 0
    for chunk in chunks:
        text = search_text_for(chunk)
        document = chunk.document
        # The passage itself is the strongest evidence.  Titles and headings
        # still contribute, but must not outrank a chunk that states the rule.
        vector = (
            SearchVector(Value(chunk.content), config="simple", weight="A")
            + SearchVector(Value(document.title), config="simple", weight="B")
            + SearchVector(Value(" ".join(chunk.heading_path)), config="simple", weight="B")
            + SearchVector(Value(" ".join(document.category)), config="simple", weight="D")
        )
        KnowledgeChunk.objects.filter(pk=chunk.pk).update(
            search_label=search_label_for(chunk),
            search_text=text,
            search_vector=vector,
        )
        count += 1
    return count


class KeywordResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    score: float
    source_id: str
    document_title: str
    effective_year: int | None
    document_status: str
    effective_from: date | None
    effective_to: date | None
    heading_path: list[str]
    canonical_url: str
    content: str


class KeywordRetriever:
    default_top_k = 5

    def search(
        self,
        query: str,
        *,
        top_k: int = default_top_k,
        effective_year: int | None = None,
        document_status: str | None = None,
        effective_on: date | None = None,
        category: str | None = None,
    ) -> list[KeywordResult]:
        terms = keyword_terms(query)
        if not terms:
            raise ValueError("query must contain at least one meaningful keyword")
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")

        ts_query = SearchQuery(terms[0], config="simple", search_type="plain")
        for term in terms[1:]:
            ts_query |= SearchQuery(term, config="simple", search_type="plain")
        filters = Q(search_vector=ts_query)
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
            .annotate(rank=SearchRank("search_vector", ts_query, cover_density=True))
            .order_by("-rank", "chunk_id")[:top_k]
        )
        return [
            KeywordResult(
                chunk_id=record.chunk_id,
                score=float(record.rank),
                source_id=record.document.source_id,
                document_title=record.document.title,
                effective_year=record.document.effective_year,
                document_status=record.document.document_status,
                effective_from=record.document.effective_from,
                effective_to=record.document.effective_to,
                heading_path=record.heading_path,
                canonical_url=record.document.canonical_url,
                content=record.content,
            )
            for record in records
        ]


class FuzzyRetriever:
    """Typo-tolerant candidate discovery over titles and section names only."""

    def search(self, query: str, *, top_k: int = 5) -> list[KeywordResult]:
        terms = keyword_terms(query)
        if not terms:
            raise ValueError("query must contain at least one meaningful keyword")
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        # Use the longest supplied term: it has the most typo-discriminating
        # trigrams, without a Korean synonym or spelling dictionary in code.
        term = max(terms, key=len)
        records = (
            KnowledgeChunk.objects.annotate(similarity=TrigramSimilarity("search_label", term))
            .filter(similarity__gt=0)
            .select_related("document")
            .order_by("-similarity", "chunk_id")[:top_k]
        )
        return [
            KeywordResult(
                chunk_id=record.chunk_id, score=float(record.similarity), source_id=record.document.source_id,
                document_title=record.document.title, effective_year=record.document.effective_year,
                document_status=record.document.document_status, heading_path=record.heading_path,
                effective_from=record.document.effective_from, effective_to=record.document.effective_to,
                canonical_url=record.document.canonical_url, content=record.content,
            )
            for record in records
        ]
