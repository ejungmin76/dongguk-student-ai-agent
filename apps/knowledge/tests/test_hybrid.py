from datetime import date

from django.test import TestCase

from apps.knowledge.models import EMBEDDING_DIMENSIONS, KnowledgeChunk, KnowledgeDocument
from apps.knowledge.services.fts import refresh_fts
from apps.knowledge.services.hybrid import HybridRetriever
from apps.knowledge.services.retrieval import DenseRetriever


def vector(first: float, second: float = 0.0) -> list[float]:
    return [first, second, *([0.0] * (EMBEDDING_DIMENSIONS - 2))]


class FakeQueryEmbedder:
    model_name = "fake-gemini-embedding"
    dimensions = EMBEDDING_DIMENSIONS

    def embed_query(self, query: str) -> list[float]:
        return vector(1.0)


class HybridRetrieverTests(TestCase):
    def setUp(self):
        current = KnowledgeDocument.objects.create(
            source_id="current-guide", title="2026 수강신청 및 졸업학점 안내", canonical_url="https://example.test/current",
            source_type="pdf", category=["graduation"], effective_year=2026, document_status="active",
            effective_from=date(2026, 3, 1), content_hash="a" * 64,
        )
        archived = KnowledgeDocument.objects.create(
            source_id="archived-guide", title="2025 수강신청 안내", canonical_url="https://example.test/archived",
            source_type="pdf", category=["enrollment"], effective_year=2025, document_status="archived",
            effective_to=date(2026, 2, 28), content_hash="b" * 64,
        )
        self._chunk(current, "both", vector(1.0), "수강신청", "수강신청 최대 학점은 18학점입니다.")
        self._chunk(current, "dense-only", vector(0.9), "기타", "신청 가능한 학점 안내입니다.")
        self._chunk(archived, "keyword-only", vector(0.1), "수강신청", "수강신청 절차를 확인하세요.")
        refresh_fts(KnowledgeChunk.objects.select_related("document").all())

    @staticmethod
    def _chunk(document, chunk_id, embedding, heading, content):
        KnowledgeChunk.objects.create(
            document=document, chunk_id=chunk_id, heading_path=[heading], section_ordinal=0, chunk_ordinal=0,
            content=content, content_hash=(chunk_id[0] * 64), embedding=embedding, embedding_model="fake-gemini-embedding",
        )

    def test_rrf_promotes_a_chunk_ranked_by_both_retrievers(self):
        response = HybridRetriever(DenseRetriever(FakeQueryEmbedder())).search("수강신청", top_k=3)

        self.assertEqual(response.results[0].chunk_id, "both")
        self.assertEqual(response.results[0].dense_rank, 1)
        self.assertEqual(response.results[0].keyword_rank, 1)
        self.assertGreater(response.results[0].rrf_score, response.results[1].rrf_score)

    def test_metadata_filters_apply_before_both_candidate_searches(self):
        response = HybridRetriever(DenseRetriever(FakeQueryEmbedder())).search(
            "수강신청", top_k=3, effective_year=2026, document_status="active",
            effective_on=date(2026, 9, 1), category="graduation",
        )

        self.assertEqual([result.chunk_id for result in response.results], ["both", "dense-only"])

    def test_rejects_invalid_requested_result_count(self):
        with self.assertRaises(ValueError):
            HybridRetriever(DenseRetriever(FakeQueryEmbedder())).search("수강신청", top_k=21)
