from datetime import date

from django.test import TestCase

from agent.schemas.status import ResultStatus
from apps.knowledge.models import EMBEDDING_DIMENSIONS, KnowledgeChunk, KnowledgeDocument
from apps.knowledge.services.fts import refresh_fts
from apps.knowledge.services.hybrid import HybridRetriever
from apps.knowledge.services.retrieval import DenseRetriever
from tools.knowledge.search_schemas import UniversityKnowledgeSearchInput
from tools.knowledge.search_university_knowledge import (
    UniversityKnowledgeSearchTool,
    build_search_university_knowledge_tool,
)


def vector(first: float, second: float = 0.0) -> list[float]:
    return [first, second, *([0.0] * (EMBEDDING_DIMENSIONS - 2))]


class FakeQueryEmbedder:
    model_name = "fake-gemini-embedding"
    dimensions = EMBEDDING_DIMENSIONS

    def embed_query(self, query: str) -> list[float]:
        return vector(1.0)


class UniversityKnowledgeSearchToolTests(TestCase):
    def setUp(self):
        current = KnowledgeDocument.objects.create(
            source_id="official-guide-2026", title="2026 수강신청 안내", canonical_url="https://example.test/guide",
            source_type="pdf", category=["enrollment"], effective_year=2026, document_status="active",
            effective_from=date(2026, 3, 1), content_hash="a" * 64,
        )
        archived = KnowledgeDocument.objects.create(
            source_id="archived-guide-2025", title="2025 수강신청 안내", canonical_url="https://example.test/archive",
            source_type="pdf", category=["enrollment"], effective_year=2025, document_status="archived",
            effective_to=date(2026, 2, 28), content_hash="b" * 64,
        )
        self._chunk(current, "current-first", vector(1.0), 3, "수강신청 최대 학점은 18학점입니다.")
        self._chunk(current, "current-second", vector(0.9), 4, "수강신청 변경 기간을 확인하세요.")
        self._chunk(archived, "archived", vector(0.1), 2, "수강신청 안내입니다.")
        refresh_fts(KnowledgeChunk.objects.select_related("document").all())
        self.tool = UniversityKnowledgeSearchTool(HybridRetriever(DenseRetriever(FakeQueryEmbedder())))

    @staticmethod
    def _chunk(document, chunk_id, embedding, page, content):
        KnowledgeChunk.objects.create(
            document=document, chunk_id=chunk_id, heading_path=["수강신청"], section_ordinal=0, chunk_ordinal=0,
            page_start=page, page_end=page, content=content, content_hash=(chunk_id[0] * 64),
            embedding=embedding, embedding_model="fake-gemini-embedding",
        )

    def test_returns_standard_success_with_deduplicated_official_sources(self):
        result = self.tool.execute(UniversityKnowledgeSearchInput(question="수강신청"))

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertGreaterEqual(len(result.data.results), 1)
        self.assertEqual(result.sources[0].source_id, "official-guide-2026")
        self.assertEqual(len({source.source_id for source in result.sources}), len(result.sources))
        self.assertEqual(result.sources[0].page, 3)
        self.assertEqual(result.sources[0].effective_at, date(2026, 3, 1))

    def test_forwards_year_and_date_filters_to_hybrid_retrieval(self):
        result = self.tool.execute(
            UniversityKnowledgeSearchInput(question="수강신청", effective_year=2026, effective_on=date(2026, 9, 1))
        )

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual({item.source_id for item in result.data.results}, {"official-guide-2026"})

    def test_returns_unavailable_when_no_official_evidence_matches(self):
        result = self.tool.execute(
            UniversityKnowledgeSearchInput(question="수강신청", effective_year=1999)
        )

        self.assertEqual(result.status, ResultStatus.UNAVAILABLE)
        self.assertEqual(result.errors[0].code, "KNOWLEDGE_NOT_FOUND")

    def test_build_function_is_json_serializable_and_adk_compatible(self):
        function_tool = build_search_university_knowledge_tool(
            HybridRetriever(DenseRetriever(FakeQueryEmbedder()))
        )

        result = function_tool("수강신청", effective_year=2026, effective_on="2026-09-01")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sources"][0]["source_type"], "university_document")
