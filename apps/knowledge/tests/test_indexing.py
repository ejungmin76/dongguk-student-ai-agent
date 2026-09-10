from __future__ import annotations

from pathlib import Path

from django.test import TestCase

from apps.knowledge.models import KnowledgeChunk as StoredKnowledgeChunk
from apps.knowledge.models import KnowledgeDocument
from apps.knowledge.services.indexing import index_chunks, load_chunks


FIXTURE = Path(__file__).parents[3] / "tests" / "fixtures" / "knowledge" / "chunking_document.md"


class FakeEmbedder:
    model_name = "fake-gemini-embedding"
    dimensions = 768

    def __init__(self) -> None:
        self.calls = 0

    def embed_documents(self, chunks):
        self.calls += 1
        return [[float(index)] * self.dimensions for index, _ in enumerate(chunks, start=1)]


class KnowledgeIndexingTests(TestCase):
    def setUp(self):
        chunk_file = self._write_fixture_chunks()
        self.payloads = load_chunks(chunk_file)

    def _write_fixture_chunks(self):
        # The committed fixture is processed with the real chunker so this test
        # covers the actual JSONL handoff used by the management command.
        from tempfile import TemporaryDirectory
        from tools.knowledge.chunking import chunk_cleaned_directory

        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        cleaned = root / "cleaned"
        cleaned.mkdir()
        (cleaned / "guide.md").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        output = root / "chunks.jsonl"
        chunk_cleaned_directory(cleaned, output)
        return output

    def test_new_chunks_are_embedded_and_persisted_with_vector_dimension(self):
        embedder = FakeEmbedder()

        result = index_chunks(self.payloads, embedder=embedder)

        self.assertEqual(result.documents, 1)
        self.assertEqual(result.created_chunks, len(self.payloads))
        self.assertEqual(result.embedded_chunks, len(self.payloads))
        self.assertEqual(KnowledgeDocument.objects.count(), 1)
        stored = StoredKnowledgeChunk.objects.get(chunk_id=self.payloads[0].chunk_id)
        self.assertEqual(len(stored.embedding), 768)
        self.assertEqual(stored.embedding_model, "fake-gemini-embedding")

    def test_identical_reprocessing_skips_existing_embeddings(self):
        first = FakeEmbedder()
        index_chunks(self.payloads, embedder=first)
        second = FakeEmbedder()

        result = index_chunks(self.payloads, embedder=second)

        self.assertEqual(result.created_chunks, 0)
        self.assertEqual(result.embedded_chunks, 0)
        self.assertEqual(result.skipped_embeddings, len(self.payloads))
        self.assertEqual(second.calls, 0)

    def test_changed_content_reembeds_only_the_changed_chunk(self):
        index_chunks(self.payloads, embedder=FakeEmbedder())
        changed = self.payloads[0].model_copy(update={"content": self.payloads[0].content + " 변경 안내"})
        embedder = FakeEmbedder()

        result = index_chunks([changed, *self.payloads[1:]], embedder=embedder)

        self.assertEqual(result.updated_chunks, 1)
        self.assertEqual(result.embedded_chunks, 1)
        self.assertEqual(embedder.calls, 1)

    def test_reprocessing_removes_stale_chunks_for_a_processed_document(self):
        index_chunks(self.payloads, embedder=FakeEmbedder())

        result = index_chunks(self.payloads[:1], embedder=FakeEmbedder())

        self.assertEqual(result.deleted_chunks, len(self.payloads) - 1)
        self.assertEqual(StoredKnowledgeChunk.objects.count(), 1)
