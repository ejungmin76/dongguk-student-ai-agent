from datetime import date
import json

from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.services.fts import KeywordRetriever


class Command(BaseCommand):
    help = "Search official university knowledge by exact Korean terms and metadata."

    def add_arguments(self, parser):
        parser.add_argument("query")
        parser.add_argument("--top-k", type=int, default=5)
        parser.add_argument("--effective-year", type=int)
        parser.add_argument("--document-status", choices=["active", "archived", "unknown"])
        parser.add_argument("--effective-on", type=date.fromisoformat)
        parser.add_argument("--category")

    def handle(self, *args, **options):
        try:
            results = KeywordRetriever().search(
                options["query"], top_k=options["top_k"], effective_year=options["effective_year"],
                document_status=options["document_status"], effective_on=options["effective_on"], category=options["category"],
            )
        except ValueError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps([item.model_dump() for item in results], ensure_ascii=False, indent=2))
