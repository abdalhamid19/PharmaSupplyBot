"""Filtering operations for prevented items."""

from __future__ import annotations

from typing import Iterable

from .item_text import normalize_code, normalize_name, normalized_key
from .utils.excel import Item
from .prevented_items_constants import PreventedItem
from .prevented_items_helpers import normalized_prevented_key


def add_prevented_item(
    prevented_items: list[PreventedItem],
    code: object,
    name: object,
) -> list[PreventedItem]:
    """Return the prevented list with one item added if it is not already present."""
    from .item_text import display_code_text, normalized_cell_text
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
) -> Iterable[Item]:
    """Yield order items excluding any products in the prevented list."""
    blocked_codes = {normalize_code(item.code) for item in prevented_items if item.code}
    code_only_blocks = {
        normalize_code(item.code)
        for item in prevented_items
        if item.code and not item.name
    }
    blocked_names = {normalize_name(item.name) for item in prevented_items if item.name}

    for item in items:
        if not _is_prevented_order_item(
            item, blocked_codes, code_only_blocks, blocked_names
        ):
            yield item


def _is_prevented_order_item(
    item: Item,
    blocked_codes: set[str],
    code_only_blocks: set[str],
    blocked_names: set[str],
) -> bool:
    """Return whether one order item is blocked by the prevented list."""
    item_code, item_name = normalized_key(item.code, item.name)
    if item_name in blocked_names:
        return True
    if item_code and item_name:
        return item_code in code_only_blocks
    if item_code:
        return item_code in blocked_codes
    return False


def is_prevented_items_excel_path(
    excel_path: Path,
    prevented_items_path,
) -> bool:
    """Return whether the order source path points at the prevented-items list."""
    from .prevented_items_constants import DEFAULT_PREVENTED_ITEMS_PATH
    if prevented_items_path is None:
        prevented_items_path = DEFAULT_PREVENTED_ITEMS_PATH
    from .prevented_items_helpers import _normalized_path
    return _normalized_path(excel_path) == _normalized_path(prevented_items_path)


__all__ = [
    "add_prevented_item",
    "remove_prevented_item",
    "filter_prevented_order_items",
    "_is_prevented_order_item",
    "is_prevented_items_excel_path",
]
