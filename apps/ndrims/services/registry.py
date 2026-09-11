from apps.ndrims.models import NdrimsMenu
from apps.ndrims.repositories import NdrimsMenuRepository, NdrimsMenuSeed


class NdrimsMenuRegistry:
    """Load verified nDRIMS menu data without embedding account-specific information."""

    def __init__(self, repository: NdrimsMenuRepository):
        self.repository = repository

    def upsert_catalog(self, seeds: list[NdrimsMenuSeed]) -> list[NdrimsMenu]:
        pending = {seed.menu_key: seed for seed in seeds}
        saved: dict[str, NdrimsMenu] = {}
        while pending:
            progressed = False
            for menu_key, seed in list(pending.items()):
                if seed.parent_key is not None and seed.parent_key not in saved:
                    continue
                saved[menu_key] = self.repository.upsert(seed, saved.get(seed.parent_key))
                del pending[menu_key]
                progressed = True
            if not progressed:
                unresolved = ", ".join(sorted(pending))
                raise ValueError(f"Unknown or cyclic nDRIMS menu parent: {unresolved}")
        return list(saved.values())
