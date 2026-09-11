"""ADK-compatible official-university-knowledge search tool contract."""

from __future__ import annotations

import os
from time import monotonic
from typing import Callable
from uuid import uuid4

from agent.schemas.error import ErrorDetail
from agent.schemas.meta import ResultMeta
from agent.schemas.result import ToolResult
from agent.schemas.source import SourceReference, SourceType
from agent.schemas.status import ResultStatus
from apps.knowledge.services.embedding import EmbeddingError, GeminiDocumentEmbedder
from apps.knowledge.services.hybrid import HybridRetriever
from apps.knowledge.services.retrieval import DenseRetriever

from .search_schemas import (
    UniversityKnowledgeSearchData,
    UniversityKnowledgeSearchHit,
    UniversityKnowledgeSearchInput,
)


TOOL_NAME = "search_university_knowledge"


class UniversityKnowledgeSearchTool:
    """Return only retrieved official evidence and citation metadata, never an LLM answer."""

    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever

    def execute(
        self, request: UniversityKnowledgeSearchInput
    ) -> ToolResult[UniversityKnowledgeSearchData]:
        started_at = monotonic()
        execution_id = str(uuid4())
        try:
            response = self.retriever.search(
                request.question,
                top_k=request.top_k,
                effective_year=request.effective_year,
                effective_on=request.effective_on,
            )
        except (EmbeddingError, ValueError) as error:
            return self._unavailable(
                execution_id,
                started_at,
                "KNOWLEDGE_SEARCH_UNAVAILABLE",
                f"공식 지식 검색을 실행할 수 없습니다: {error}",
                retryable=True,
            )

        if not response.results:
            return self._unavailable(
                execution_id,
                started_at,
                "KNOWLEDGE_NOT_FOUND",
                "질문에 대응하는 공식 자료를 찾지 못했습니다.",
            )

        data = UniversityKnowledgeSearchData(
            results=[
                UniversityKnowledgeSearchHit(
                    chunk_id=item.chunk_id,
                    content=item.content,
                    heading_path=item.heading_path,
                    rrf_score=item.rrf_score,
                    dense_rank=item.dense_rank,
                    keyword_rank=item.keyword_rank,
                    source_id=item.source_id,
                    document_title=item.document_title,
                    canonical_url=item.canonical_url,
                    effective_year=item.effective_year,
                    document_status=item.document_status,
                    effective_from=item.effective_from,
                    effective_to=item.effective_to,
                    page_start=item.page_start,
                    page_end=item.page_end,
                )
                for item in response.results
            ],
            dense_duration_ms=response.dense_duration_ms,
            keyword_duration_ms=response.keyword_duration_ms,
            fusion_duration_ms=response.fusion_duration_ms,
        )
        return ToolResult[UniversityKnowledgeSearchData](
            status=ResultStatus.SUCCESS,
            data=data,
            sources=self._sources(data.results),
            meta=self._meta(execution_id, started_at),
        )

    @staticmethod
    def _sources(results: list[UniversityKnowledgeSearchHit]) -> list[SourceReference]:
        """One citation per official document, preserving the first retrieved page when known."""

        sources: list[SourceReference] = []
        seen_source_ids: set[str] = set()
        for result in results:
            if result.source_id in seen_source_ids:
                continue
            seen_source_ids.add(result.source_id)
            sources.append(
                SourceReference(
                    source_id=result.source_id,
                    source_type=SourceType.UNIVERSITY_DOCUMENT,
                    title=result.document_title,
                    url=result.canonical_url,
                    page=result.page_start,
                    effective_at=result.effective_from,
                )
            )
        return sources

    @staticmethod
    def _meta(execution_id: str, started_at: float) -> ResultMeta:
        return ResultMeta(
            tool_name=TOOL_NAME,
            execution_id=execution_id,
            duration_ms=max(0, round((monotonic() - started_at) * 1000)),
        )

    def _unavailable(
        self,
        execution_id: str,
        started_at: float,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> ToolResult[UniversityKnowledgeSearchData]:
        return ToolResult[UniversityKnowledgeSearchData](
            status=ResultStatus.UNAVAILABLE,
            errors=[ErrorDetail(code=code, message=message, retryable=retryable)],
            meta=self._meta(execution_id, started_at),
        )


def build_search_university_knowledge_tool(
    retriever: HybridRetriever | None = None,
) -> Callable[..., dict]:
    """Build a JSON-returning function ready for ADK registration in issue #24."""

    service = UniversityKnowledgeSearchTool(
        retriever
        or HybridRetriever(
            DenseRetriever(
                GeminiDocumentEmbedder(
                    os.getenv("GEMINI_API_KEY", ""),
                    model_name=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"),
                )
            )
        )
    )

    def search_university_knowledge(
        question: str,
        effective_year: int | None = None,
        effective_on: str | None = None,
        top_k: int = 5,
    ) -> dict:
        """공식 동국대학교 문서를 Hybrid RRF로 검색하고 인용 가능한 출처를 반환한다.

        Args:
            question: 학생의 원문 질문 또는 Planner가 만든 검색 질의.
            effective_year: 적용 교육과정·문서 연도. 학생 프로필에서 확인된 값만 사용한다.
            effective_on: 적용 기준일(YYYY-MM-DD). 질문의 시점이 명확할 때만 사용한다.
            top_k: 반환할 공식 근거 청크 수(1~5).
        """
        request = UniversityKnowledgeSearchInput(
            question=question,
            effective_year=effective_year,
            effective_on=effective_on,
            top_k=top_k,
        )
        return service.execute(request).model_dump(mode="json")

    return search_university_knowledge
