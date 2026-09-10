from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from tools.knowledge.chunking import ChunkingConfig, chunk_cleaned_directory


class Command(BaseCommand):
    help = "Split cleaned university knowledge documents into section-aware JSONL chunks."

    def add_arguments(self, parser):
        parser.add_argument("--input-dir", type=Path, default=settings.BASE_DIR / "data" / "knowledge" / "cleaned")
        parser.add_argument("--output", type=Path, default=settings.BASE_DIR / "data" / "knowledge" / "chunks" / "chunks.jsonl")
        parser.add_argument("--max-chars", type=int, default=1200)
        parser.add_argument("--overlap-chars", type=int, default=150)

    def handle(self, *args, **options):
        input_dir: Path = options["input_dir"]
        if not input_dir.is_dir():
            raise CommandError(f"Cleaned knowledge directory not found: {input_dir}")
        config = ChunkingConfig(
            max_chars=options["max_chars"],
            overlap_chars=options["overlap_chars"],
        )
        chunks = chunk_cleaned_directory(input_dir, options["output"], config)
        self.stdout.write(self.style.SUCCESS(f"OK   {len(chunks)} chunks: {options['output']}"))
