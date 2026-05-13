"""Excel parsing for Tawreed cart-removal items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import openpyxl

from .item_text import (
    display_code_text,
    normalize_name,
    normalized_cell_text,
    normalized_key,
)

REMOVE_ITEMS_DIR = Path("data/input") / "remove_items"
DEFAULT_REMOVE_ITEMS_PATH = REMOVE_ITEMS_DIR / "remove.xlsx"
REMOVE_CODE_COLUMN = "كود"
REMOVE_NAME_COLUMN = "إسم الصنف"


@dataclass(frozen=True)
class CartRemovalItem:
    """One product that should be removed from Tawreed carts."""

    code: str
    name: str


def load_cart_removal_items(
    path: Path = DEFAULT_REMOVE_ITEMS_PATH,
) -> Iterable[CartRemovalItem]:
    """Yield cart-removal items from an XLSX file using openpyxl."""
    if not path.exists(): return
    with open(path, "rb") as f:
        workbook = openpyxl.load_workbook(f, read_only=True, data_only=True)
        try:
            sheet = workbook.active
            rows = sheet.iter_rows(min_row=1, values_only=True)
            yield from _parse_cart_removal_rows(rows, path)
        finally: workbook.close()


def _parse_cart_removal_rows(rows, path) -> Iterable[CartRemovalItem]:
    """Parse Excel rows into CartRemovalItem objects."""
    header = [str(cell).strip() if cell else "" for cell in next(rows)]
    try:
        code_idx, name_idx = header.index(REMOVE_CODE_COLUMN), header.index(REMOVE_NAME_COLUMN)
    except ValueError:
        raise KeyError(f"Missing columns in {path}. Found: {header}")
    seen_keys: set[tuple[str, str]] = set()
    for row in rows:
        code, name = display_code_text(row[code_idx]), normalized_cell_text(row[name_idx])
        if not name: continue
        key = normalized_key(code, name)
        if key not in seen_keys:
            seen_keys.add(key)
            yield CartRemovalItem(code=code, name=name)



def cart_row_matches_item(row_text: str, item: CartRemovalItem) -> bool:
    """Return whether one cart row text appears to belong to the removal item by name."""
    return cart_row_matches_names(row_text, [item.name])


def cart_row_matches_names(row_text: str, names: list[str]) -> bool:
    """Return whether one cart row text contains any normalized item name."""
    normalized_text = normalize_name(row_text)
    for name in names:
        normalized_name = normalize_name(name)
        if normalized_name and normalized_name in normalized_text:
            return True
    return False
