"""Constants and dataclass for prevented items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PREVENTED_ITEMS_DIR = Path("data/input") / "prevented_items"
DEFAULT_PREVENTED_ITEMS_PATH = PREVENTED_ITEMS_DIR / "drugprevented.xlsx"
PREVENTED_CODE_COLUMN = "كود"
PREVENTED_NAME_COLUMN = "إسم الصنف"


@dataclass(frozen=True)
class PreventedItem:
    """One product that should not be ordered from Tawreed."""

    code: str
    name: str


__all__ = [
    "PREVENTED_ITEMS_DIR",
    "DEFAULT_PREVENTED_ITEMS_PATH",
    "PREVENTED_CODE_COLUMN",
    "PREVENTED_NAME_COLUMN",
    "PreventedItem",
]
