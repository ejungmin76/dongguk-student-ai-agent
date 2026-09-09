from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from tools.knowledge.cleaning import clean_pdf_pages
from tools.knowledge.models import DownloadedSource, KnowledgeSource
from tools.knowledge.pipeline import KnowledgePipeline, load_catalog


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "knowledge"


def source(source_type: str = "html") -> KnowledgeSource:
    return KnowledgeSource(
        source_id="fixture-source",
        title="학사 안내",
        url="https://example.test/notice",
        source_type=source_type,
        category=["enrollment"],
        priority="P0",
        enabled=True,
        metadata={"publisher": "동국대학교"},
    )


class KnowledgeCleaningTests(SimpleTestCase):
    def test_pdf_cleaning_removes_repeated_margins_and_keeps_korean_table_and_list(self):
        pages = json.loads((FIXTURE_DIR / "academic_guide_pdf_pages.json").read_text(encoding="utf-8"))

        cleaned = clean_pdf_pages(pages)

        self.assertNotIn("동국대학교 2026학년도 학업이수가이드", cleaned)
        self.assertNotIn("교무처 학사지원팀", cleaned)
        self.assertIn("수강신청은 정해진 기간에 합니다.", cleaned)
        self.assertIn("| 등급 | 평점 |", cleaned)
        self.assertIn("1. 취득학점을 확인합니다.", cleaned)


class KnowledgePipelineTests(SimpleTestCase):
    def test_catalog_loads_only_enabled_sources(self):
        catalog = Path(__file__).parents[1] / "docs" / "university-knowledge-sources.yaml"

        sources = load_catalog(catalog)

        self.assertGreaterEqual(len(sources), 1)
        self.assertTrue(all(item.enabled for item in sources))
        self.assertEqual(len(sources), len({item.source_id for item in sources}))

    def test_html_parser_preserves_table_list_and_korean_and_removes_layout_noise(self):
        raw_html = (FIXTURE_DIR / "academic_notice.html").read_bytes()
        with TemporaryDirectory() as temporary_directory:
            pipeline = KnowledgePipeline(output_dir=Path(temporary_directory), request_interval_seconds=0)
            downloaded = DownloadedSource(
                source=source(),
                content=raw_html,
                content_type="text/html",
                fetched_at=datetime.now(UTC).isoformat(),
                content_hash="fixture-hash",
                raw_path=Path(temporary_directory) / "raw" / "fixture-source.html",
            )

            document = pipeline.normalize(downloaded)
            saved_path = pipeline.persist(document)

            self.assertIn("# 2026학년도 수강신청 안내", document.content)
            self.assertIn("- nDRIMS에 로그인합니다.", document.content)
            self.assertIn("| 구분 | 최대 학점 |", document.content)
            self.assertIn("| 일반 학생 | 18 |", document.content)
            self.assertNotIn("메인메뉴", document.content)
            self.assertNotIn("개인정보처리방침", document.content)
            self.assertEqual(document.content.count("수강신청 기간은 8월 3일부터 8월 7일까지입니다."), 1)
            self.assertTrue(saved_path.is_file())
            self.assertTrue((Path(temporary_directory) / "manifests" / "fixture-source.json").is_file())

    def test_pdf_normalization_uses_extractor_pages_then_cleans(self):
        pages = json.loads((FIXTURE_DIR / "academic_guide_pdf_pages.json").read_text(encoding="utf-8"))
        with TemporaryDirectory() as temporary_directory:
            pipeline = KnowledgePipeline(output_dir=Path(temporary_directory), request_interval_seconds=0)
            downloaded = DownloadedSource(
                source=source("pdf"),
                content=b"%PDF-fixture",
                content_type="application/pdf",
                fetched_at=datetime.now(UTC).isoformat(),
                content_hash="fixture-pdf-hash",
                raw_path=Path(temporary_directory) / "raw" / "fixture-source.pdf",
            )
            class FakePage:
                def __init__(self, text):
                    self.text = text

                def get_text(self, _mode):
                    return self.text

            class FakePdf:
                metadata = {"title": "2026 학업이수가이드"}

                def __iter__(self):
                    return iter([FakePage(page) for page in pages])

            with patch("tools.knowledge.pipeline.pymupdf.open", return_value=FakePdf()):
                document = pipeline.normalize(downloaded)

        self.assertEqual(document.page_count, 3)
        self.assertEqual(document.title, "2026 학업이수가이드")
        self.assertIn("성적 안내", document.content)
        self.assertIn("| A+ | 4.5 |", document.content)
