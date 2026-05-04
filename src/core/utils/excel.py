"""Excel parsing utilities for Tawreed order items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ..config.config_models import ExcelConfig


@dataclass(frozen=True)
class Item:
    """One requested product row loaded from the shortage Excel sheet."""

    code: str
    name: str
    qty: int


def load_items_from_excel(path: Path, config: ExcelConfig, limit: int = 0) -> list[Item]:
    """Load order items from an Excel sheet using the configured column mapping."""
    dataframe = _read_excel_with_headers(path, config)
    items: list[Item] = []
    for row in dataframe.itertuples(index=False, name=None):
        item = _row_tuple_to_item(row, config)
        if item is None:
            continue
        items.append(item)
        if limit and len(items) >= limit:
            break
    return items


def _read_excel(path: Path, **read_kwargs: Any) -> pd.DataFrame:
    """Read the Excel file from disk."""
    if not path.exists():
        raise FileNotFoundError(f"Excel not found: {path}")
    return pd.read_excel(path, **read_kwargs)


def _read_excel_with_headers(path: Path, config: ExcelConfig) -> pd.DataFrame:
    """Read one Excel file while avoiding a full-sheet fallback on title-row exports."""
    header_row_index = _detect_header_row(path, config)
    usecols = [config.code_col, config.name_col, config.qty_col]
    try:
        return _read_excel(
            path,
            usecols=usecols,
            header=header_row_index if header_row_index is not None else 0,
        )
    except ValueError as error:
        raise KeyError(
            f"Missing one or more required Excel columns {usecols}. Original error: {error}"
        ) from error


def _detect_header_row(path: Path, config: ExcelConfig) -> int | None:
    """Find the likely header row in report-style exports."""
    preview = _read_excel(path, header=None, nrows=20)
    required_columns = {config.code_col, config.name_col, config.qty_col}
    identity_columns = {config.code_col, config.name_col}
    best_partial_match: int | None = None

    for row_index, row in preview.iterrows():
        values = {str(value).strip() for value in row.dropna().tolist()}
        if required_columns.issubset(values):
            return int(row_index)
        if best_partial_match is None and identity_columns.issubset(values):
            best_partial_match = int(row_index)

    return best_partial_match


def _row_tuple_to_item(row: tuple, config: ExcelConfig) -> Item | None:
    """Convert one Excel row tuple to an order item when it passes filters."""
    code = str(row[0] or "").strip()
    name = str(row[1] or "").strip()
    quantity = _bounded_quantity(row[2], config)
    if not code and not name:
        return None
    if quantity < config.min_qty:
        return None
    return Item(code=code, name=name, qty=quantity)


def _bounded_quantity(value: Any, config: ExcelConfig) -> int:
    """Clamp the requested quantity to the configured Excel limits."""
    quantity = _to_int(value)
    return min(quantity, config.max_qty)


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
