from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from tools.knowledge.chunking import ChunkingConfig, chunk_cleaned_directory, chunk_markdown


FIXTURE = Path(__file__).parent / "fixtures" / "knowledge" / "chunking_document.md"


class KnowledgeChunkingTests(SimpleTestCase):
    def setUp(self):
        self.document = FIXTURE.read_text(encoding="utf-8")

    def test_heading_paths_and_source_metadata_are_preserved(self):
        chunks = chunk_markdown(self.document)

        credit_chunk = next(chunk for chunk in chunks if "18학점" in chunk.content)
        graduation_chunk = next(chunk for chunk in chunks if "최소 취득학점" in chunk.content)
        self.assertEqual(credit_chunk.heading_path, ["수강신청", "신청 가능 학점"])
        self.assertEqual(credit_chunk.effective_year, 2026)
        self.assertEqual(credit_chunk.page_start, 10)
        self.assertEqual(graduation_chunk.heading_path, ["졸업", "졸업학점"])
        self.assertEqual(graduation_chunk.page_start, 12)
        self.assertTrue(credit_chunk.chunk_id.startswith("fixture-academic-guide:"))

    def test_chunk_size_uses_overlap_without_crossing_a_section(self):
        body = "\n\n".join(f"문장 {number}: 학사 안내를 확인합니다." for number in range(40))
        markdown = self.document.replace("일반 학생은 학기당 최대 18학점까지 신청할 수 있다.", body)

        chunks = chunk_markdown(markdown, ChunkingConfig(max_chars=300, overlap_chars=60))
        section_chunks = [chunk for chunk in chunks if chunk.heading_path[-1] == "신청 가능 학점"]
        self.assertGreater(len(section_chunks), 1)
        self.assertTrue(all(len(chunk.content) <= 300 for chunk in section_chunks))
        self.assertIn("문장", section_chunks[0].content)
        self.assertIn("문장", section_chunks[1].content)
        self.assertNotIn("정정 기간", "\n".join(chunk.content for chunk in section_chunks))

    def test_directory_output_is_jsonl(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            cleaned = root / "cleaned"
            cleaned.mkdir()
            (cleaned / "guide.md").write_text(self.document, encoding="utf-8")
            output = root / "chunks" / "chunks.jsonl"

            chunks = chunk_cleaned_directory(cleaned, output)
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(rows), len(chunks))
        self.assertEqual(rows[0]["source_id"], "fixture-academic-guide")
        self.assertIn("heading_path", rows[0])
