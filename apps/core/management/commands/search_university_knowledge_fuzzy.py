import json

from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.services.fts import FuzzyRetriever


class Command(BaseCommand):
    help = "Find typo-tolerant university knowledge candidates from official labels."

    def add_arguments(self, parser):
        parser.add_argument("query")
        parser.add_argument("--top-k", type=int, default=5)

    def handle(self, *args, **options):
        try:
            results = FuzzyRetriever().search(options["query"], top_k=options["top_k"])
        except ValueError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps([item.model_dump() for item in results], ensure_ascii=False, indent=2))
