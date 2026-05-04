"""Excel parsing utilities for Tawreed order items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import openpyxl

from ..config.config_models import ExcelConfig


@dataclass(frozen=True)
class Item:
    """One requested product row loaded from the shortage Excel sheet."""

    code: str
    name: str
    qty: int


def load_items_from_excel(
    path: Path, config: ExcelConfig, limit: int = 0
) -> Iterable[Item]:
    """Yield order items from an Excel sheet using the configured column mapping."""
    count = 0
    for row in _read_item_rows(path, config):
        item = _row_tuple_to_item(row, config)
        if item is None:
            continue
        yield item
        count += 1
        if limit and count >= limit:
            break


def _read_item_rows(path: Path, config: ExcelConfig) -> Iterable[tuple]:
    """Yield only the configured Excel item columns as row tuples using openpyxl."""
    header_row_index = _detect_header_row(path, config)
    if header_row_index is None:
        header_row_index = 0

    with open(path, "rb") as f:
        workbook = openpyxl.load_workbook(f, read_only=True, data_only=True)
        try:
            sheet = workbook.active
            # Map column names to indices
            col_map = {}
            header_row = list(
                sheet.iter_rows(
                    min_row=header_row_index + 1, max_row=header_row_index + 1, values_only=True
                )
            )[0]
            for idx, cell in enumerate(header_row):
                if cell:
                    col_map[str(cell).strip()] = idx

            required_cols = [config.code_col, config.name_col, config.qty_col]
            indices = [col_map.get(col) for col in required_cols]

            if any(idx is None for idx in indices):
                missing = [col for col, idx in zip(required_cols, indices) if idx is None]
                raise KeyError(
                    f"Missing one or more required Excel columns {required_cols}. Original error: columns not found {missing}"
                )

            # Iterate rows starting after header
            for row in sheet.iter_rows(min_row=header_row_index + 2, values_only=True):
                yield tuple(row[idx] for idx in indices)
        finally:
            workbook.close()







def _detect_header_row(path: Path, config: ExcelConfig) -> int | None:
    """Find the likely header row in report-style exports using openpyxl."""
    required_columns = {config.code_col, config.name_col, config.qty_col}
    identity_columns = {config.code_col, config.name_col}
    best_partial_match: int | None = None

    with open(path, "rb") as f:
        workbook = openpyxl.load_workbook(f, read_only=True, data_only=True)
        try:
            sheet = workbook.active
            for row_index, row in enumerate(sheet.iter_rows(max_row=20, values_only=True)):
                values = {str(value).strip() for value in row if value is not None}
                if required_columns.issubset(values):
                    return row_index
                if best_partial_match is None and identity_columns.issubset(values):
                    best_partial_match = row_index
        finally:
            workbook.close()

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
    if x is None or (isinstance(x, float) and x != x):  # x != x is NaN check
        return 0
    try:
        return int(round(float(x)))
    except Exception:
        s = str(x).strip()
        if not s:
            return 0
        return int(float(s))

