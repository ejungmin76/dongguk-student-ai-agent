from apps.ndrims.models import NdrimsMenu

from .dto import NdrimsMenuSeed


class DjangoNdrimsMenuRepository:
    def upsert(self, seed: NdrimsMenuSeed, parent: NdrimsMenu | None) -> NdrimsMenu:
        menu, _ = NdrimsMenu.objects.get_or_create(
            menu_key=seed.menu_key,
            defaults={
                "title": seed.title,
                "parent": parent,
                "sort_order": seed.sort_order,
                "source_url": seed.source_url,
                "verified_at": seed.verified_at,
                "external_menu_id": seed.external_menu_id,
            },
        )
        menu.title = seed.title
        menu.parent = parent
        menu.sort_order = seed.sort_order
        menu.source_url = seed.source_url
        menu.verified_at = seed.verified_at
        menu.external_menu_id = seed.external_menu_id
        menu.is_active = True
        menu.full_clean()
        menu.save()
        return menu
