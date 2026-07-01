"""Build order-search items from corrected manual-review rows."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .utils.excel import Item


def corrected_items_from_manual_review_csv(path: Path) -> list[Item]:
    """Return match-only items from rows containing manual correction fields."""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return corrected_items_from_manual_review_rows(csv.DictReader(file))


def corrected_items_from_manual_review_rows(rows: Iterable[dict]) -> list[Item]:
    """Return unique corrected items from edited manual-review rows."""
    return _unique_items(_item_from_row(row) for row in rows if _has_correction(row))


def write_corrected_review_csv(rows: list[dict], path: Path) -> Path:
    """Write corrected manual-review rows to a CSV used by order --match-only."""
    selected = [row for row in rows if _has_correction(row)]
    if not selected:
        raise ValueError("No corrected manual-review rows selected.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=sorted(_fieldnames(selected)))
        writer.writeheader()
        writer.writerows(selected)
    return path


def _has_correction(row: dict) -> bool:
    if _clean(row.get("not_matching")).lower() in {"1", "true", "yes", "y"}:
        return False
    return any(
        _clean(row.get(key))
        for key in ("correct_query", "correct_product_name", "correct_store_product_id")
    )


def _item_from_row(row: dict) -> Item:
    return Item(
        _clean(row.get("item_code")),
        _corrected_name(row),
        _quantity(row.get("item_qty") or row.get("qty")),
    )


def _corrected_name(row: dict) -> str:
    return (
        _clean(row.get("correct_query"))
        or _clean(row.get("correct_product_name"))
        or _clean(row.get("item_name"))
    )


def _quantity(value: object) -> int:
    try:
        return max(1, int(float(str(value or 1))))
    except ValueError:
        return 1


def _unique_items(items: Iterable[Item]) -> list[Item]:
    seen: set[tuple[str, str]] = set()
    out = []
    for item in items:
        key = (_clean(item.code).lower(), _clean(item.name).lower())
        if item.name and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _fieldnames(rows: list[dict]) -> set[str]:
    return {str(key) for row in rows for key in row}


def _clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text
