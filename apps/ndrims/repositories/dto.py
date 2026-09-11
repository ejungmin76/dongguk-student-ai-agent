from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class NdrimsMenuSeed:
    menu_key: str
    title: str
    parent_key: str | None
    sort_order: int
    source_url: str
    verified_at: date
    external_menu_id: str = ""
