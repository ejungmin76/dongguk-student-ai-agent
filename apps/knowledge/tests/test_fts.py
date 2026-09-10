from datetime import date

from django.test import TestCase

from apps.knowledge.models import KnowledgeChunk, KnowledgeDocument
from apps.knowledge.services.fts import KeywordRetriever, keyword_terms, refresh_fts


class KeywordRetrieverTests(TestCase):
    def setUp(self):
        current = KnowledgeDocument.objects.create(
            source_id="guide-2026", title="2026 컴퓨터 AI 학업이수 안내", canonical_url="https://example.test/2026",
            source_type="pdf", category=["graduation", "curriculum"], effective_year=2026,
            document_status="active", effective_from=date(2026, 3, 1), content_hash="a" * 64,
        )
        archived = KnowledgeDocument.objects.create(
            source_id="guide-2025", title="2025 재수강 안내", canonical_url="https://example.test/2025",
            source_type="html", category=["grades"], effective_year=2025,
            document_status="archived", effective_to=date(2026, 2, 28), content_hash="b" * 64,
        )
        self.current_chunk = KnowledgeChunk.objects.create(
            document=current, chunk_id="current-retake", heading_path=["성적", "재수강"], section_ordinal=0,
            chunk_ordinal=0, content="컴퓨터 AI학부 학생의 재수강 및 졸업학점 안내입니다.", content_hash="c" * 64,
        )
        self.archived_chunk = KnowledgeChunk.objects.create(
            document=archived, chunk_id="archived-retake", heading_path=["재수강"], section_ordinal=0,
            chunk_ordinal=0, content="재수강은 C+ 이하 과목에 신청할 수 있습니다.", content_hash="d" * 64,
        )
        refresh_fts(KnowledgeChunk.objects.select_related("document").all())

    def test_korean_terms_are_normalized_without_a_fixed_keyword_list(self):
        self.assertEqual(keyword_terms("컴퓨터·AI학부 재수강 알려줘"), ["컴퓨터", "ai학부", "재수강"])

    def test_exact_keyword_search_returns_matching_documents(self):
        results = KeywordRetriever().search("재수강")

        self.assertEqual({item.chunk_id for item in results}, {"current-retake", "archived-retake"})

    def test_metadata_filters_combine_year_status_date_and_category(self):
        results = KeywordRetriever().search(
            "컴퓨터", effective_year=2026, document_status="active", effective_on=date(2026, 9, 1), category="graduation"
        )

        self.assertEqual([item.chunk_id for item in results], ["current-retake"])
