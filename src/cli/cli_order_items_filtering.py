"""Order item filtering and slicing functions."""

from __future__ import annotations

import itertools
from typing import Iterable

from ..core.utils.excel import Item
from .cli_order_items_summary import summary_label, processed_summary_item_keys, item_key


def slice_items(items: Iterable[Item], args) -> Iterable[Item]:
    start_item = max(1, getattr(args, "start_item", 1))
    end_item = getattr(args, "end_item", 0)
    
    if start_item > 1:
        items = itertools.islice(items, start_item - 1, None)
        
    if end_item >= start_item:
        slice_limit = end_item - start_item + 1
        items = itertools.islice(items, slice_limit)
        
    return items


def excel_load_limit(args, has_prevented_filter: bool) -> int:
    """Return the safe Excel read limit before profile-level filters run."""
    if bool(getattr(args, "resume", False)) or has_prevented_filter:
        return 0
    if getattr(args, "start_item", 1) > 1 or getattr(args, "end_item", 0) > 0:
        return 0
    return order_item_limit(args)


def prepared_order_items(
    profile_key: str, items: Iterable[Item], args
) -> Iterable[Item]:
    """Yield one profile's remaining order items after session and resume checks."""
    from .cli_shared import require_state_file
    require_state_file(profile_key)
    if not bool(getattr(args, "resume", False)):
        yield from items
        return
    processed_keys = processed_summary_item_keys(profile_key, summary_label(args))
    for item in items:
        if item_key(item.code, item.name) not in processed_keys:
            yield item


def limited_order_items(items: Iterable[Item], args) -> Iterable[Item]:
    """Apply the per-run item limit after prevented/resume filters."""
    limit = order_item_limit(args)
    if limit <= 0:
        return items
    return itertools.islice(items, limit)


def order_item_limit(args) -> int:
    """Return the requested order item processing limit."""
    return int(getattr(args, "limit", 0) or 0)


def match_only(args) -> bool:
    """Return whether this order run should only evaluate product matches."""
    return bool(getattr(args, "match_only", False))


def ensure_non_empty_items(
    profile_key: str,
    items: Iterable[Item],
) -> Iterable[Item] | None:
    """Return an iterable that is guaranteed to yield at least one item, else None."""
    _, probe_iter = itertools.tee(items)
    try:
        first_item = next(probe_iter)
    except StopIteration:
        print(f"[{profile_key}] No remaining items to process.")
        return None
    return itertools.chain([first_item], probe_iter)


__all__ = [
    "slice_items",
    "excel_load_limit",
    "prepared_order_items",
    "limited_order_items",
    "order_item_limit",
    "match_only",
    "ensure_non_empty_items",
]

