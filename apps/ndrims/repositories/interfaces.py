from typing import Protocol

from apps.ndrims.models import NdrimsMenu

from .dto import NdrimsMenuSeed


class NdrimsMenuRepository(Protocol):
    def upsert(self, seed: NdrimsMenuSeed, parent: NdrimsMenu | None) -> NdrimsMenu: ...
