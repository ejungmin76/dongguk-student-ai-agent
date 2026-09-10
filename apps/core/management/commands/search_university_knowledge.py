from __future__ import annotations

import json
import os

from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.services.embedding import EmbeddingError, GeminiDocumentEmbedder
from apps.knowledge.services.retrieval import DenseRetriever


class Command(BaseCommand):
    help = "Find the most semantically similar official university knowledge chunks."

    def add_arguments(self, parser):
        parser.add_argument("query", help="Student question in Korean or English.")
        parser.add_argument("--top-k", type=int, default=5, help="Number of candidates to return (default: 5).")

    def handle(self, *args, **options):
        try:
            embedder = GeminiDocumentEmbedder(
                os.getenv("GEMINI_API_KEY", ""),
                model_name=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"),
            )
            results = DenseRetriever(embedder).search(options["query"], top_k=options["top_k"])
        except (EmbeddingError, ValueError) as error:
            raise CommandError(str(error)) from error

        self.stdout.write(json.dumps([item.model_dump() for item in results], ensure_ascii=False, indent=2))
