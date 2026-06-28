"""Persistent prevented-item list helpers for Tawreed orders."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .item_text import normalize_code, normalize_name, normalized_key
from .utils.excel import Item
from .prevented_items_constants import (
    PREVENTED_ITEMS_DIR,
    DEFAULT_PREVENTED_ITEMS_PATH,
    PREVENTED_CODE_COLUMN,
    PREVENTED_NAME_COLUMN,
    PreventedItem,
)
from .prevented_items_io import load_prevented_items, save_prevented_items
from .prevented_items_filtering import (
    add_prevented_item,
    remove_prevented_item,
    filter_prevented_order_items,
    is_prevented_items_excel_path,
)
from .prevented_items_helpers import normalized_prevented_key


__all__ = [
    "PREVENTED_ITEMS_DIR",
    "DEFAULT_PREVENTED_ITEMS_PATH",
    "PREVENTED_CODE_COLUMN",
    "PREVENTED_NAME_COLUMN",
    "PreventedItem",
    "load_prevented_items",
    "save_prevented_items",
    "add_prevented_item",
    "remove_prevented_item",
    "filter_prevented_order_items",
    "is_prevented_items_excel_path",
    "normalized_prevented_key",
]
