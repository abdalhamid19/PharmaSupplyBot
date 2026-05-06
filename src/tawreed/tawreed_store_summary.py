"""Selected Tawreed store summary helpers for order-result artifacts."""

from __future__ import annotations

from typing import Any, Iterable

from .tawreed_constants import NESTED_NAME_KEYS, NESTED_STORE_KEYS, STORE_NAME_KEYS
from .tawreed_pricing import first_discount_value, format_discount_percent


def record_selected_stores(
    bot, selections: Iterable[tuple[dict[str, Any], int]]
) -> None:
    """Persist selected multi-store summary values on the active bot."""
    selected = list(selections)
    bot.last_selected_discount_percent = _joined_selection_values(
        selected, store_discount_percent
    )
    bot.last_selected_store_name = _joined_selection_values(selected, store_name)


def record_single_store(bot, store: dict[str, Any]) -> None:
    """Persist selected single-store summary values on the active bot."""
    bot.last_selected_discount_percent = store_discount_percent(store)
    bot.last_selected_store_name = store_name(store)


def store_name(store: dict[str, Any]) -> str:
    """Extract a human-readable Tawreed store or supplier name."""
    for key in STORE_NAME_KEYS:
        value = str(store.get(key) or "").strip()
        if value:
            return value
    for object_key in NESTED_STORE_KEYS:
        nested = store.get(object_key)
        if isinstance(nested, dict):
            value = _first_nested_name(nested)
            if value:
                return value
    return ""


def store_discount_percent(store: dict[str, Any]) -> str:
    """Return the store discount formatted for order-result summaries."""
    return format_discount_percent(first_discount_value(store))


def _first_nested_name(source: dict[str, Any]) -> str:
    for key in NESTED_NAME_KEYS:
        value = str(source.get(key) or "").strip()
        if value:
            return value
    return ""


def _joined_selection_values(selections, extractor) -> str:
    parts = []
    for store, quantity in selections:
        value = extractor(store)
        if value:
            parts.append(f"{value} (qty {int(quantity)})")
    return " | ".join(parts)
