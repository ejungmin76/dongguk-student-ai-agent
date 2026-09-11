from datetime import date

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from apps.ndrims.models import NdrimsMenu


class NdrimsMenuRegistryTests(TestCase):
    def test_breadcrumb_uses_verified_parent_nodes(self):
        root = NdrimsMenu.objects.create(
            menu_key="course-registration", title="수강신청", sort_order=1,
            source_url="https://ndrims.dongguk.edu/main/main.clx", verified_at=date(2026, 9, 11),
        )
        menu = NdrimsMenu.objects.create(
            menu_key="course-registration-history", title="수강신청내역확인", parent=root, sort_order=1,
            source_url="https://ndrims.dongguk.edu/main/main.clx", verified_at=date(2026, 9, 11),
        )

        self.assertEqual(menu.breadcrumb, ["수강신청", "수강신청내역확인"])

    def test_only_official_ndrims_host_can_be_a_menu_source(self):
        menu = NdrimsMenu(
            menu_key="invalid-source", title="잘못된 출처", source_url="https://example.test/menu",
            verified_at=date(2026, 9, 11),
        )

        with self.assertRaises(ValidationError):
            menu.full_clean()

    def test_seed_is_idempotent_and_includes_observed_course_history_menu(self):
        call_command("seed_ndrims_menus")
        first_count = NdrimsMenu.objects.count()
        call_command("seed_ndrims_menus")

        menu = NdrimsMenu.objects.get(menu_key="course-registration-history")
        self.assertEqual(first_count, 150)
        self.assertEqual(NdrimsMenu.objects.count(), first_count)
        self.assertEqual(menu.breadcrumb, ["수강신청", "수강신청내역확인"])
        self.assertTrue(menu.is_active)
