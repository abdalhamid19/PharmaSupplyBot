"""Store and warehouse selection helpers for Tawreed ordering flows."""

from __future__ import annotations

import re
from typing import Any


def choose_store_index(
    stores: list[dict[str, Any]],
    mode: str,
    skip_exception_cls: type[Exception],
) -> int:
    """Choose the store index according to the configured warehouse strategy."""
    if not stores:
        raise RuntimeError("No stores available for selected product.")
    if mode == "first_available":
        return _first_available_store_index(stores, skip_exception_cls)
    if mode == "max_available":
        return _max_available_store_index(stores, skip_exception_cls)
    if mode == "max_discount":
        return _max_discount_store_index(stores, skip_exception_cls)
    raise ValueError(f"Unknown warehouse strategy mode: {mode}")


def max_available_warehouse_row(rows, available_quantity_selector: str) -> int:
    """Return the row index with the highest displayed warehouse quantity."""
    best_index = 0
    best_quantity = -1
    for row_index in range(rows.count()):
        quantity = warehouse_row_quantity(rows.nth(row_index), available_quantity_selector)
        if quantity > best_quantity:
            best_quantity = quantity
            best_index = row_index
    return best_index


def warehouse_row_quantity(row, available_quantity_selector: str) -> int:
    """Parse the numeric quantity from a warehouse row."""
    text = row.locator(available_quantity_selector).first.inner_text(timeout=1000).strip()
    try:
        return int(float(text.replace(",", "")))
    except Exception:
        return 0


def _first_available_store_index(
    stores: list[dict[str, Any]],
    skip_exception_cls: type[Exception],
) -> int:
    """Return the first store index that still has stock."""
    for store_index, store in enumerate(stores):
        if int(store.get("availableQuantity") or 0) > 0:
            return store_index
    raise skip_exception_cls("All available stores for this product are out of stock.")


def _max_available_store_index(
    stores: list[dict[str, Any]],
    skip_exception_cls: type[Exception],
) -> int:
    """Return the store index with the largest available quantity."""
    best_index = 0
    best_quantity = -1
    for store_index, store in enumerate(stores):
        quantity = int(store.get("availableQuantity") or 0)
        if quantity > best_quantity:
            best_quantity = quantity
            best_index = store_index
    if best_quantity <= 0:
        raise skip_exception_cls("All available stores for this product are out of stock.")
    return best_index


def _max_discount_store_index(
    stores: list[dict[str, Any]],
    skip_exception_cls: type[Exception],
) -> int:
    """Return the available store index with the largest discount percent."""
    best_index = 0
    best_sort_key = (-1.0, -1)
    for store_index, store in enumerate(stores):
        quantity = int(store.get("availableQuantity") or 0)
        if quantity <= 0:
            continue
        sort_key = (_store_discount_value(store), quantity)
        if sort_key > best_sort_key:
            best_sort_key = sort_key
            best_index = store_index
    if best_sort_key[1] <= 0:
        raise skip_exception_cls("All available stores for this product are out of stock.")
    return best_index


def _store_discount_value(store: dict[str, Any]) -> float:
    """Return a comparable percent discount value from one store payload."""
    for key in ("discountPercent", "discountPercentage", "discountRate", "discountValue", "discount"):
        if key not in store:
            continue
        value = store.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, str):
            number_match = re.search(r"-?\d+(?:[.,]\d+)?", value.strip())
            if not number_match:
                continue
            value = float(number_match.group(0).replace(",", "."))
        try:
            number = float(value)
        except Exception:
            continue
        return number * 100 if 0 < number < 1 else number
    return -1.0
