from __future__ import annotations

import json
import os
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.services.embedding import EmbeddingError, GeminiDocumentEmbedder
from apps.knowledge.services.hybrid import HybridRetriever
from apps.knowledge.services.retrieval import DenseRetriever


class Command(BaseCommand):
    help = "Fuse dense and keyword official-knowledge searches with deterministic RRF."

    def add_arguments(self, parser):
        parser.add_argument("query")
        parser.add_argument("--top-k", type=int, default=5)
        parser.add_argument("--effective-year", type=int)
        parser.add_argument("--document-status", choices=["active", "archived", "unknown"])
        parser.add_argument("--effective-on", type=date.fromisoformat)
        parser.add_argument("--category")

    def handle(self, *args, **options):
        try:
            embedder = GeminiDocumentEmbedder(
                os.getenv("GEMINI_API_KEY", ""),
                model_name=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"),
            )
            response = HybridRetriever(DenseRetriever(embedder)).search(
                options["query"],
                top_k=options["top_k"],
                effective_year=options["effective_year"],
                document_status=options["document_status"],
                effective_on=options["effective_on"],
                category=options["category"],
            )
        except (EmbeddingError, ValueError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps(response.model_dump(), ensure_ascii=False, indent=2))
