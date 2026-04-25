"""Excel parsing utilities for Tawreed order items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .config_models import ExcelConfig


@dataclass(frozen=True)
class Item:
    """One requested product row loaded from the shortage Excel sheet."""

    code: str
    name: str
    qty: int


def _to_int(x: Any) -> int:
    """Convert a spreadsheet cell to an integer quantity with empty-safe fallbacks."""
    if x is None:
        return 0
    try:
        if pd.isna(x):
            return 0
    except Exception:
        pass
    try:
        return int(round(float(x)))
    except Exception:
        s = str(x).strip()
        if not s:
            return 0
        return int(float(s))


def load_items_from_excel(path: Path, config: ExcelConfig, limit: int = 0) -> list[Item]:
    """Load order items from an Excel sheet using the configured column mapping."""
    dataframe = _read_excel(path)
    _require_columns(dataframe, config)
    items: list[Item] = []
    for _, row in dataframe.iterrows():
        item = _row_to_item(row, config)
        if item is None:
            continue
        items.append(item)
        if limit and len(items) >= limit:
            break

    return items


def _read_excel(path: Path) -> pd.DataFrame:
    """Read the Excel file from disk."""
    if not path.exists():
        raise FileNotFoundError(f"Excel not found: {path}")
    return pd.read_excel(path)


def _require_columns(dataframe: pd.DataFrame, config: ExcelConfig) -> None:
    """Ensure the configured Excel columns exist in the sheet."""
    for column_name in (config.code_col, config.name_col, config.qty_col):
        if column_name in dataframe.columns:
            continue
        raise KeyError(
            f"Missing required column '{column_name}' in Excel. "
            f"Found: {list(dataframe.columns)}"
        )


def _row_to_item(row: Any, config: ExcelConfig) -> Item | None:
    """Convert one spreadsheet row to an order item when it passes filters."""
    code = str(row.get(config.code_col, "")).strip()
    name = str(row.get(config.name_col, "")).strip()
    quantity = _bounded_quantity(row.get(config.qty_col), config)
    if not code and not name:
        return None
    if quantity < config.min_qty:
        return None
    return Item(code=code, name=name, qty=quantity)


def _bounded_quantity(value: Any, config: ExcelConfig) -> int:
    """Clamp the requested quantity to the configured Excel limits."""
    quantity = _to_int(value)
    return min(quantity, config.max_qty)

