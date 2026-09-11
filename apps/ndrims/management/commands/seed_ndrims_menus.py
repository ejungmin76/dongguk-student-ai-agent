from datetime import date
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError

from apps.ndrims.repositories import DjangoNdrimsMenuRepository, NdrimsMenuSeed
from apps.ndrims.services import NdrimsMenuRegistry


class Command(BaseCommand):
    help = "Upsert verified student-visible nDRIMS menu data."

    @staticmethod
    def _date(value: str | date) -> date:
        return value if isinstance(value, date) else date.fromisoformat(value)

    def handle(self, *args, **options):
        catalog_path = Path(__file__).resolve().parents[2] / "seed_data" / "student_menus.yaml"
        try:
            raw_items = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
            seeds = [
                NdrimsMenuSeed(
                    menu_key=item["menu_key"],
                    title=item["title"],
                    parent_key=item.get("parent_key"),
                    sort_order=item["sort_order"],
                    source_url=item["source_url"],
                    verified_at=self._date(item["verified_at"]),
                    external_menu_id=item.get("external_menu_id", ""),
                )
                for item in raw_items
            ]
            menus = NdrimsMenuRegistry(DjangoNdrimsMenuRepository()).upsert_catalog(seeds)
        except (KeyError, TypeError, ValueError, yaml.YAMLError) as error:
            raise CommandError(f"Invalid nDRIMS menu catalog: {error}") from error
        self.stdout.write(self.style.SUCCESS(f"nDRIMS 메뉴 동기화 완료: {len(menus)}개"))
