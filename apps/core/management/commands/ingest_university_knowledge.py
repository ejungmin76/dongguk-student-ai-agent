from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from tools.knowledge.pipeline import KnowledgePipeline, load_catalog


class Command(BaseCommand):
    help = "Download and normalize enabled public university knowledge sources."

    def add_arguments(self, parser):
        parser.add_argument("--catalog", type=Path, default=settings.BASE_DIR / "docs" / "university-knowledge-sources.yaml")
        parser.add_argument("--output-dir", type=Path, default=settings.BASE_DIR / "data" / "knowledge")
        parser.add_argument("--source", action="append", dest="source_ids", help="Process one source id; can be repeated.")
        parser.add_argument("--all", action="store_true", help="Include catalog entries marked enabled: false.")
        parser.add_argument("--interval", type=float, default=3.0, help="Seconds between source requests (default: 3).")

    def handle(self, *args, **options):
        catalog_path: Path = options["catalog"]
        if not catalog_path.is_file():
            raise CommandError(f"Catalog not found: {catalog_path}")

        sources = load_catalog(catalog_path, enabled_only=not options["all"])
        selected_ids = set(options.get("source_ids") or [])
        if selected_ids:
            sources = [source for source in sources if source.source_id in selected_ids]
            missing = selected_ids - {source.source_id for source in sources}
            if missing:
                raise CommandError(f"Unknown or disabled source id(s): {', '.join(sorted(missing))}")
        if not sources:
            raise CommandError("No sources selected.")

        pipeline = KnowledgePipeline(output_dir=options["output_dir"], request_interval_seconds=options["interval"])
        results = pipeline.ingest_all(sources)
        failed = []
        for source_id, result in results.items():
            if isinstance(result, Exception):
                failed.append(source_id)
                self.stderr.write(self.style.ERROR(f"FAIL {source_id}: {result}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"OK   {source_id}: {result}"))
        if failed:
            raise CommandError(f"{len(failed)} source(s) failed: {', '.join(failed)}")
