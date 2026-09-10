from django.core.management.base import BaseCommand

from apps.knowledge.models import KnowledgeChunk
from apps.knowledge.services.fts import refresh_fts


class Command(BaseCommand):
    help = "Rebuild PostgreSQL full-text vectors for all university knowledge chunks."

    def handle(self, *args, **options):
        count = refresh_fts(KnowledgeChunk.objects.select_related("document").all())
        self.stdout.write(self.style.SUCCESS(f"OK   rebuilt FTS vectors for {count} chunks"))
