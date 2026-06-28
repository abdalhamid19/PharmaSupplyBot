"""Helper functions for prevented items."""

from __future__ import annotations

from pathlib import Path

from .item_text import (
    display_code_text,
    normalized_cell_text,
    normalized_key,
)
from .prevented_items_constants import PREVENTED_CODE_COLUMN, PREVENTED_NAME_COLUMN, PreventedItem


def _prevented_column_indices(header_row, path) -> tuple[int, int]:
    """Return prevented Excel code/name column indices."""
    header = [str(cell).strip() if cell else "" for cell in header_row]
    try:
        return header.index(PREVENTED_CODE_COLUMN), header.index(PREVENTED_NAME_COLUMN)
    except ValueError:
        raise KeyError(f"Missing columns in {path}. Found: {header}")


def _prevented_item_from_row(
    row: tuple[object, ...], code_idx: int, name_idx: int
) -> PreventedItem | None:
    """Return one prevented item from a raw Excel row when populated."""
    code = display_code_text(row[code_idx])
    name = normalized_cell_text(row[name_idx])
    if not code and not name:
        return None
    return PreventedItem(code=code, name=name)


def normalized_prevented_key(item: PreventedItem) -> tuple[str, str]:
    """Return the comparable identity for one prevented item."""
    return normalized_key(item.code, item.name)


def _normalized_path(path: Path) -> Path:
    """Return an absolute path for reliable same-file comparisons."""
    return path.expanduser().resolve(strict=False)


__all__ = [
    "_prevented_column_indices",
    "_prevented_item_from_row",
    "normalized_prevented_key",
    "_normalized_path",
]
