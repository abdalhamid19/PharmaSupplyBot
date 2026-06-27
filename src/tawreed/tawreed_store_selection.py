"""Store selection and discount calculation for Tawreed orders."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .tawreed_pricing import discount_value_as_percent, first_discount_value
from .tawreed_store_summary import store_name


@dataclass(frozen=True)
class StoreChoice:
    """One precomputed store candidate for split-quantity selection."""

    index: int
    store: dict[str, Any]
    identity: str
    available_quantity: int
    discount_percent: float
    priority_score: int = 999  # 1=highest priority, 999=unknown

def available_store_choices(stores: list[dict[str, Any]], used_store_ids: set[str] | None = None, min_discount_percent: float = 0.0, preferred_warehouses: list[str] | None = None) -> list[StoreChoice]:
    """Return unused stores that have stock and satisfy the minimum discount."""
    used_ids, preferred = used_store_ids or set(), preferred_warehouses or []
    return [c for c in _all_store_choices(stores, preferred) if c.identity not in used_ids and c.available_quantity > 0 and c.discount_percent >= min_discount_percent - 0.001]

def choose_next_store_for_remaining_quantity(stores: list[dict[str, Any]], used_store_ids: set[str] | None = None, mode: str = "first_available", skip_exception_cls: type[Exception] = RuntimeError, min_discount_percent: float = 0.0, preferred_warehouses: list[str] | None = None) -> StoreChoice | None:
    """Choose the next store for a remaining item quantity."""
    choices = available_store_choices(stores, used_store_ids, min_discount_percent, preferred_warehouses)
    if choices:
        return _select_choice(choices, mode)
    if available_store_choices(stores, None, min_discount_percent, preferred_warehouses):
        return None
    raise skip_exception_cls(_empty_selection_reason(min_discount_percent))

def _select_choice(choices: list[StoreChoice], mode: str) -> StoreChoice:
    tier = lambda c: round(c.discount_percent / 0.3) * 0.3
    if mode == "first_available":
        return choices[0]
    if mode == "max_available":
        return max(choices, key=lambda c: (c.available_quantity, tier(c), -c.priority_score))
    if mode == "max_discount":
        return max(choices, key=lambda c: (tier(c), -c.priority_score, c.available_quantity))
    raise ValueError(f"Unknown warehouse strategy mode: {mode}")

def _all_store_choices(
    stores: list[dict[str, Any]], preferred_warehouses: list[str]
) -> list[StoreChoice]:
    return [_store_choice(i, s, preferred_warehouses) for i, s in enumerate(stores)]

def _store_choice(index: int, store: dict[str, Any], preferred_warehouses: list[str]) -> StoreChoice:
    return StoreChoice(index=index, store=store, identity=_store_identity(index, store), available_quantity=_available_quantity(store), discount_percent=_discount_percent(store), priority_score=_calculate_priority_score(store_name(store), preferred_warehouses))

def _store_identity(index: int, store: dict[str, Any]) -> str:
    for key in ("storeProductId", "productStoreId", "storeId", "supplierId", "id"):
        value = str(store.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    return f"storeName:{store_name(store)}:{index}"

def _available_quantity(store: dict[str, Any]) -> int:
    try:
        qty_str = str(store.get("availableQuantity") or 0).replace(",", "")
        return int(float(qty_str))
    except (TypeError, ValueError):
        return 0

def _discount_percent(store: dict[str, Any]) -> float:
    return max(0.0, discount_value_as_percent(first_discount_value(store)))

def _empty_selection_reason(min_discount_percent: float) -> str:
    if min_discount_percent > 0:
        return f"No available store meets minimum discount {min_discount_percent:g}%."
    return "All available stores for this product are out of stock."

def _normalize_store_name(name: str) -> str:
    """Normalize store name for fuzzy matching."""
    return re.sub(r"\s+", " ", re.sub(r"[^\u0600-\u06FF\s()]", "", name.strip())).lower()

def _stores_match(name1: str, name2: str) -> bool:
    """Check if two store names match using fuzzy logic."""
    n1, n2 = _normalize_store_name(name1), _normalize_store_name(name2)
    return n1 == n2 or n1 in n2 or n2 in n1

def _calculate_priority_score(store_name_value: str, preferred_list: list[str]) -> int:
    """Calculate priority score. 1=highest, 999=unknown."""
    for index, preferred_name in enumerate(preferred_list, start=1):
        if _stores_match(store_name_value, preferred_name):
            return index
    return 999
