"""Persistent prevented-item list helpers for Tawreed orders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .utils.excel import Item

PREVENTED_ITEMS_DIR = Path("data/input") / "prevented_items"
DEFAULT_PREVENTED_ITEMS_PATH = PREVENTED_ITEMS_DIR / "drugprevented.xlsx"
PREVENTED_CODE_COLUMN = "كود"
PREVENTED_NAME_COLUMN = "إسم الصنف"


@dataclass(frozen=True)
class PreventedItem:
    """One product that should not be ordered from Tawreed."""

    code: str
    name: str


def load_prevented_items(path: Path = DEFAULT_PREVENTED_ITEMS_PATH) -> list[PreventedItem]:
    """Load prevented items from an XLSX file."""
    if not path.exists():
        return []
    dataframe = pd.read_excel(path)
    _require_prevented_columns(dataframe)
    prevented_items: list[PreventedItem] = []
    seen_keys: set[tuple[str, str]] = set()
    for row in dataframe.to_dict(orient="records"):
        item = _row_to_prevented_item(row)
        if item is None:
            continue
        key = normalized_prevented_key(item)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        prevented_items.append(item)
    return prevented_items


def save_prevented_items(
    prevented_items: list[PreventedItem],
    path: Path = DEFAULT_PREVENTED_ITEMS_PATH,
) -> Path:
    """Save the prevented list to disk as an XLSX file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe = pd.DataFrame(
        [
            {
                PREVENTED_CODE_COLUMN: item.code,
                PREVENTED_NAME_COLUMN: item.name,
            }
            for item in prevented_items
        ],
        columns=[PREVENTED_CODE_COLUMN, PREVENTED_NAME_COLUMN],
    )
    dataframe.to_excel(path, index=False)
    return path


def add_prevented_item(
    prevented_items: list[PreventedItem],
    code: object,
    name: object,
) -> list[PreventedItem]:
    """Return the prevented list with one item added if it is not already present."""
    item = PreventedItem(code=display_code_text(code), name=normalized_cell_text(name))
    if not item.code and not item.name:
        return prevented_items
    existing_keys = {normalized_prevented_key(existing) for existing in prevented_items}
    if normalized_prevented_key(item) in existing_keys:
        return prevented_items
    return [*prevented_items, item]


def remove_prevented_item(
    prevented_items: list[PreventedItem],
    code: object,
    name: object,
) -> list[PreventedItem]:
    """Return the prevented list without the matching item."""
    remove_key = normalized_key(code, name)
    return [
        item for item in prevented_items if normalized_prevented_key(item) != remove_key
    ]


def filter_prevented_order_items(
    items: Iterable[Item],
    prevented_items: list[PreventedItem],
) -> tuple[Iterable[Item], int]:
    """Return an iterable of order items excluding any products in the prevented list."""
    blocked_codes = {
        normalize_code(item.code) for item in prevented_items if normalize_code(item.code)
    }
    blocked_names = {
        normalize_name(item.name) for item in prevented_items if normalize_name(item.name)
    }

    # Since we need to return the skipped_count, we must consume the generator or wrap it.
    # To maintain true RAM efficiency, we should ideally NOT return skipped_count immediately.
    # But for now, we'll build a list to avoid breaking the CLI summary.
    allowed_items: list[Item] = []
    skipped_count = 0
    for item in items:
        item_code = normalize_code(item.code)
        item_name = normalize_name(item.name)
        if item_code:
            is_prevented = item_code in blocked_codes
        else:
            is_prevented = item_name in blocked_names

        if is_prevented:
            skipped_count += 1
            continue
        allowed_items.append(item)
    return allowed_items, skipped_count


def is_prevented_items_excel_path(
    excel_path: Path,
    prevented_items_path: Path = DEFAULT_PREVENTED_ITEMS_PATH,
) -> bool:
    """Return whether the order source path points at the prevented-items list."""
    return _normalized_path(excel_path) == _normalized_path(prevented_items_path)


def normalized_prevented_key(item: PreventedItem) -> tuple[str, str]:
    """Return the comparable identity for one prevented item."""
    return normalized_key(item.code, item.name)


def normalized_key(code: object, name: object) -> tuple[str, str]:
    """Return a normalized product key."""
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
    """Return code text suitable for saving/displaying."""
    text = normalized_cell_text(value)
    if text.endswith(".0"):
        return text[:-2]
    return text


def _normalized_path(path: Path) -> Path:
    """Return an absolute path for reliable same-file comparisons."""
    return path.expanduser().resolve(strict=False)


def _require_prevented_columns(dataframe: pd.DataFrame) -> None:
    """Ensure the prevented-items sheet has the expected columns."""
    for column_name in (PREVENTED_CODE_COLUMN, PREVENTED_NAME_COLUMN):
        if column_name in dataframe.columns:
            continue
        raise KeyError(
            f"Missing required column '{column_name}' in prevented-items Excel. "
            f"Found: {list(dataframe.columns)}"
        )


def _row_to_prevented_item(row: Any) -> PreventedItem | None:
    """Convert one XLSX row into a prevented item."""
    code = display_code_text(row.get(PREVENTED_CODE_COLUMN, ""))
    name = normalized_cell_text(row.get(PREVENTED_NAME_COLUMN, ""))
    if not code and not name:
        return None
    return PreventedItem(code=code, name=name)
