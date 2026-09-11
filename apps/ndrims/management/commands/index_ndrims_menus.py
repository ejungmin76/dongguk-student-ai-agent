import os

from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.services.embedding import EmbeddingError, GeminiDocumentEmbedder
from apps.ndrims.services import index_menu_embeddings


class Command(BaseCommand):
    help = "Create or refresh Gemini embeddings for verified nDRIMS menu paths."

    def handle(self, *args, **options):
        try:
            embedder = GeminiDocumentEmbedder(
                os.getenv("GEMINI_API_KEY", ""),
                model_name=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"),
            )
            result = index_menu_embeddings(embedder)
        except (EmbeddingError, ValueError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(
            f"nDRIMS 메뉴 임베딩 완료: 생성/갱신 {result.embedded}개, 유지 {result.skipped}개"
        ))
