"""Excel parsing for Tawreed cart-removal items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

REMOVE_ITEMS_DIR = Path("data/input") / "remove_items"
DEFAULT_REMOVE_ITEMS_PATH = REMOVE_ITEMS_DIR / "remove.xlsx"
REMOVE_CODE_COLUMN = "كود"
REMOVE_NAME_COLUMN = "إسم الصنف"


@dataclass(frozen=True)
class CartRemovalItem:
    """One product that should be removed from Tawreed carts."""

    code: str
    name: str


def load_cart_removal_items(path: Path = DEFAULT_REMOVE_ITEMS_PATH) -> list[CartRemovalItem]:
    """Load cart-removal items from an XLSX file."""
    dataframe = pd.read_excel(path)
    _require_remove_columns(dataframe)
    items: list[CartRemovalItem] = []
    seen_keys: set[tuple[str, str]] = set()
    for _, row in dataframe.iterrows():
        item = _row_to_cart_removal_item(row)
        if item is None:
            continue
        key = normalized_key(item.code, item.name)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        items.append(item)
    return items


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


def normalized_key(code: object, name: object) -> tuple[str, str]:
    """Return a normalized comparable product key."""
    return normalize_code(code), normalize_name(name)


def normalize_code(value: object) -> str:
    """Return a stable code string for comparisons."""
    text = normalized_cell_text(value).lower()
    if text in {"nan", "none"}:
        return ""
    if text.endswith(".0"):
        return text[:-2]
    return text


def normalize_name(value: object) -> str:
    """Return a stable item-name string for comparisons."""
    return " ".join(normalized_cell_text(value).lower().split())


def normalized_cell_text(value: object) -> str:
    """Return spreadsheet cell text without pandas empty-value artifacts."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def display_code_text(value: object) -> str:
    """Return code text suitable for display and reports."""
    text = normalized_cell_text(value)
    if text.endswith(".0"):
        return text[:-2]
    return text


def _require_remove_columns(dataframe: pd.DataFrame) -> None:
    """Ensure the removal sheet has the expected columns."""
    for column_name in (REMOVE_CODE_COLUMN, REMOVE_NAME_COLUMN):
        if column_name in dataframe.columns:
            continue
        raise KeyError(
            f"Missing required column '{column_name}' in cart-removal Excel. "
            f"Found: {list(dataframe.columns)}"
        )


def _row_to_cart_removal_item(row: Any) -> CartRemovalItem | None:
    """Convert one XLSX row into a cart-removal item."""
    code = display_code_text(row.get(REMOVE_CODE_COLUMN, ""))
    name = normalized_cell_text(row.get(REMOVE_NAME_COLUMN, ""))
    if not name:
        return None
    return CartRemovalItem(code=code, name=name)
