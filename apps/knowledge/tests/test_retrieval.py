from django.test import TestCase

from apps.knowledge.models import EMBEDDING_DIMENSIONS, KnowledgeChunk, KnowledgeDocument
from apps.knowledge.services.retrieval import DenseRetriever


def vector(first: float, second: float = 0.0) -> list[float]:
    return [first, second, *([0.0] * (EMBEDDING_DIMENSIONS - 2))]


class FakeQueryEmbedder:
    model_name = "fake-gemini-embedding"
    dimensions = EMBEDDING_DIMENSIONS

    def embed_query(self, query: str) -> list[float]:
        return vector(1.0)


class DenseRetrieverTests(TestCase):
    def setUp(self):
        self.document = KnowledgeDocument.objects.create(
            source_id="fixture-guide",
            title="학사 안내",
            canonical_url="https://example.test/guide",
            source_type="html",
            category=["enrollment"],
            content_hash="a" * 64,
        )
        self._chunk("course-limit", vector(1.0), "수강신청 > 신청 가능 학점", "최대 신청학점은 18학점입니다.")
        self._chunk("retake", vector(0.7, 0.7), "성적 > 재수강", "재수강 신청 방법입니다.")
        self._chunk("not-indexed", None, "장학", "임베딩이 없는 청크입니다.")

    def _chunk(self, chunk_id, embedding, heading, content):
        KnowledgeChunk.objects.create(
            document=self.document,
            chunk_id=chunk_id,
            heading_path=heading.split(" > "),
            section_ordinal=0,
            chunk_ordinal=0,
            content=content,
            content_hash="b" * 64,
            embedding=embedding,
            embedding_model="fake-gemini-embedding" if embedding else "",
        )

    def test_returns_top_k_in_cosine_similarity_order_with_citation_metadata(self):
        results = DenseRetriever(FakeQueryEmbedder()).search("몇 학점까지 신청할 수 있나요?", top_k=2)

        self.assertEqual([result.chunk_id for result in results], ["course-limit", "retake"])
        self.assertGreater(results[0].score, results[1].score)
        self.assertEqual(results[0].heading_path, ["수강신청", "신청 가능 학점"])
        self.assertEqual(results[0].canonical_url, "https://example.test/guide")

    def test_validates_blank_query_and_top_k_range(self):
        retriever = DenseRetriever(FakeQueryEmbedder())
        with self.assertRaises(ValueError):
            retriever.search("   ")
        with self.assertRaises(ValueError):
            retriever.search("학점", top_k=21)
