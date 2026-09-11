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
            catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
            source_url = catalog["source_url"]
            verified_at = self._date(catalog["verified_at"])
            seeds: list[NdrimsMenuSeed] = []
            for root_order, item in enumerate(catalog["menus"], start=1):
                root_key = item["menu_key"]
                seeds.append(NdrimsMenuSeed(
                    menu_key=root_key, title=item["title"], parent_key=None,
                    sort_order=root_order * 10, source_url=source_url, verified_at=verified_at,
                ))
                for child_order, (menu_key, title) in enumerate(item.get("children", []), start=1):
                    seeds.append(NdrimsMenuSeed(
                        menu_key=menu_key, title=title, parent_key=root_key,
                        sort_order=child_order * 10, source_url=source_url, verified_at=verified_at,
                    ))
            menus = NdrimsMenuRegistry(DjangoNdrimsMenuRepository()).upsert_catalog(seeds)
        except (KeyError, TypeError, ValueError, yaml.YAMLError) as error:
            raise CommandError(f"Invalid nDRIMS menu catalog: {error}") from error
        self.stdout.write(self.style.SUCCESS(f"nDRIMS 메뉴 동기화 완료: {len(menus)}개"))
