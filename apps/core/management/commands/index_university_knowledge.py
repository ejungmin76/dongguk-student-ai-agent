from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.services.embedding import GeminiDocumentEmbedder
from apps.knowledge.services.indexing import index_chunks, load_chunks


class Command(BaseCommand):
    help = "Store section-aware knowledge chunks and Gemini embeddings in PostgreSQL/pgvector."

    def add_arguments(self, parser):
        parser.add_argument("--chunks", type=Path, default=settings.BASE_DIR / "data" / "knowledge" / "chunks" / "chunks.jsonl")
        parser.add_argument("--batch-size", type=int, default=20)
        parser.add_argument("--skip-embeddings", action="store_true", help="Validate and store chunks without calling Gemini.")

    def handle(self, *args, **options):
        if options["batch_size"] < 1:
            raise CommandError("--batch-size must be at least 1.")
        try:
            chunks = load_chunks(options["chunks"])
        except (FileNotFoundError, ValueError) as error:
            raise CommandError(str(error)) from error

        embedder = None
        if not options["skip_embeddings"]:
            embedder = GeminiDocumentEmbedder(
                os.getenv("GEMINI_API_KEY", ""),
                model_name=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"),
            )
        result = index_chunks(chunks, embedder=embedder, batch_size=options["batch_size"])
        self.stdout.write(
            self.style.SUCCESS(
                "OK   documents={documents}, created={created_chunks}, updated={updated_chunks}, "
                "deleted={deleted_chunks}, embedded={embedded_chunks}, unchanged={skipped_embeddings}".format(**result.__dict__)
            )
        )
