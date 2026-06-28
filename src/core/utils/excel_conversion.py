"""Excel row conversion utilities for Tawreed order items."""

from typing import Any

from ..config.config_models import ExcelConfig


def _row_tuple_to_item(row: tuple, config: ExcelConfig):
    """Convert one Excel row tuple to an order item when it passes filters."""
    from .excel_main import Item
    
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
    if x is None or (isinstance(x, float) and x != x):
        return 0
    try:
        return int(round(float(x)))
    except Exception:
        s = str(x).strip()
        if not s:
            return 0
        return int(float(s))
