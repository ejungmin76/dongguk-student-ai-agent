from __future__ import annotations

import os
from time import monotonic
from typing import Callable
from uuid import uuid4

from agent.schemas.action import ActionReference, ActionType
from agent.schemas.error import ErrorDetail
from agent.schemas.meta import ResultMeta
from agent.schemas.result import ToolResult
from agent.schemas.source import SourceReference, SourceType
from agent.schemas.status import ResultStatus
from apps.knowledge.services.embedding import EmbeddingError, GeminiDocumentEmbedder
from apps.ndrims.services import NdrimsMenuRetriever

from .schemas import NdrimsMenuCandidate, NdrimsMenuSearchData, NdrimsMenuSearchInput


TOOL_NAME = "find_ndrims_menu"


class NdrimsMenuSearchTool:
    def __init__(self, retriever: NdrimsMenuRetriever):
        self.retriever = retriever

    def execute(self, request: NdrimsMenuSearchInput) -> ToolResult[NdrimsMenuSearchData]:
        started_at = monotonic()
        execution_id = str(uuid4())
        try:
            results = self.retriever.search(request.question, top_k=request.top_k)
        except (EmbeddingError, ValueError) as error:
            return self._unavailable(execution_id, started_at, "NDRIMS_MENU_SEARCH_UNAVAILABLE", str(error), True)
        if not results:
            return self._unavailable(
                execution_id,
                started_at,
                "NDRIMS_MENU_NOT_FOUND",
                "등록된 nDRIMS 메뉴에서 질문과 충분히 가까운 메뉴를 찾지 못했습니다.",
            )

        candidates = [NdrimsMenuCandidate(**item.model_dump()) for item in results]
        same_title = any(item.title == results[0].title for item in results[1:])
        close_second = len(results) > 1 and results[0].score - results[1].score <= 0.01
        data = NdrimsMenuSearchData(
            candidates=candidates,
            requires_user_selection=same_title or close_second,
        )
        return ToolResult[NdrimsMenuSearchData](
            status=ResultStatus.SUCCESS,
            data=data,
            sources=[
                SourceReference(
                    source_id="ndrims-student-menu-registry",
                    source_type=SourceType.SERVICE_REGISTRY,
                    title="동국대학교 nDRIMS 학생 메뉴",
                    url=results[0].source_url,
                )
            ],
            actions=[
                ActionReference(
                    action_id=item.menu_key,
                    action_type=ActionType.NAVIGATE_NDRIMS_MENU,
                    label=" > ".join(item.breadcrumb),
                )
                for item in results
            ],
            meta=self._meta(execution_id, started_at),
        )

    @staticmethod
    def _meta(execution_id: str, started_at: float) -> ResultMeta:
        return ResultMeta(
            tool_name=TOOL_NAME,
            execution_id=execution_id,
            duration_ms=max(0, round((monotonic() - started_at) * 1000)),
        )

    def _unavailable(self, execution_id: str, started_at: float, code: str, message: str, retryable: bool = False):
        return ToolResult[NdrimsMenuSearchData](
            status=ResultStatus.UNAVAILABLE,
            errors=[ErrorDetail(code=code, message=message, retryable=retryable)],
            meta=self._meta(execution_id, started_at),
        )


def build_find_ndrims_menu_tool(retriever: NdrimsMenuRetriever | None = None) -> Callable[..., dict]:
    service = NdrimsMenuSearchTool(
        retriever
        or NdrimsMenuRetriever(
            GeminiDocumentEmbedder(
                os.getenv("GEMINI_API_KEY", ""),
                model_name=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"),
            )
        )
    )

    def find_ndrims_menu(question: str, top_k: int = 5) -> dict:
        """학생 질문과 의미상 가까운, 서버에 등록된 nDRIMS 메뉴 경로만 반환한다.

        반환된 경로는 Chrome 확장프로그램이 로그인된 nDRIMS 탭에서 다시 검증한 뒤 이동해야 한다.
        """
        return service.execute(NdrimsMenuSearchInput(question=question, top_k=top_k)).model_dump(mode="json")

    return find_ndrims_menu
