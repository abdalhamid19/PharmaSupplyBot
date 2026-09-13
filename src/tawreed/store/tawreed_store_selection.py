"""Store selection and discount calculation for Tawreed orders."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ...core.pricing import resolve_store_prices
from ...core.ordering.warehouse_order_policy import LOWEST_PURCHASE_PRICE_MODE
from ...core.normalization.normalizer import normalize_arabic
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
    purchase_price: float | None = None

def available_store_choices(stores: list[dict[str, Any]], used_store_ids: set[str] | None = None, min_discount_percent: float = 0.0, preferred_warehouses: list[str] | None = None) -> list[StoreChoice]:
    """Return unused stocked stores meeting the configured discount floor."""
    used_ids, preferred = used_store_ids or set(), preferred_warehouses or []
    return [
        c for c in _all_store_choices(stores, preferred)
        if c.identity not in used_ids
        and c.available_quantity > 0
        and c.discount_percent >= min_discount_percent - 0.001
    ]

def choose_next_store_for_remaining_quantity(stores: list[dict[str, Any]], used_store_ids: set[str] | None = None, mode: str = LOWEST_PURCHASE_PRICE_MODE, skip_exception_cls: type[Exception] = RuntimeError, min_discount_percent: float = 0.0, preferred_warehouses: list[str] | None = None) -> StoreChoice | None:
    """Choose the next store for a remaining item quantity."""
    if mode != LOWEST_PURCHASE_PRICE_MODE:
        raise ValueError(
            "Only lowest_purchase_price is supported for warehouse selection"
        )
    choices = available_store_choices(stores, used_store_ids, min_discount_percent, preferred_warehouses)
    if choices:
        if not _lowest_price_choices(choices):
            raise skip_exception_cls("No available store has a structured purchase price.")
        return _select_choice(choices)
    if available_store_choices(stores, None, min_discount_percent, preferred_warehouses):
        return None
    raise skip_exception_cls(_empty_selection_reason(stores, min_discount_percent))

def _select_choice(choices: list[StoreChoice]) -> StoreChoice:
    priced_choices = _lowest_price_choices(choices)
    if not priced_choices:
        raise ValueError("No available store has a structured purchase price")
    preferred_choices = _best_priority_choices(priced_choices)
    return min(preferred_choices, key=lambda choice: choice.index)


def _lowest_price_choices(choices: list[StoreChoice]) -> list[StoreChoice]:
    """Keep exact-lowest-price offers; warehouse preference resolves their ties."""
    priced = [
        choice
        for choice in choices
        if choice.purchase_price is not None
        and math.isfinite(choice.purchase_price)
        and choice.purchase_price > 0
    ]
    if not priced:
        return []
    lowest_price = min(choice.purchase_price for choice in priced)
    return [choice for choice in priced if choice.purchase_price == lowest_price]


def _best_priority_choices(choices: list[StoreChoice]) -> list[StoreChoice]:
    best_priority = min(choice.priority_score for choice in choices)
    return [choice for choice in choices if choice.priority_score == best_priority]


def discount_tier(discount_percent: float) -> float:
    """Group discounts into the existing 0.3 percentage-point selection tiers."""
    return round(discount_percent / 0.3) * 0.3

def _all_store_choices(
    stores: list[dict[str, Any]], preferred_warehouses: list[str]
) -> list[StoreChoice]:
    return [_store_choice(i, s, preferred_warehouses) for i, s in enumerate(stores)]

def _store_choice(index: int, store: dict[str, Any], preferred_warehouses: list[str]) -> StoreChoice:
    return StoreChoice(
        index=index,
        store=store,
        identity=_store_identity(index, store),
        available_quantity=_available_quantity(store),
        discount_percent=_discount_percent(store),
        priority_score=calculate_warehouse_priority_score(
            store_name(store), preferred_warehouses
        ),
        purchase_price=_purchase_price(store),
    )

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


def _purchase_price(store: dict[str, Any]) -> float | None:
    for key in ("purchase_price", "purchasePrice"):
        try:
            price = float(str(store.get(key) or "").replace(",", ""))
        except (TypeError, ValueError):
            continue
        if math.isfinite(price) and price > 0:
            return price
    price = resolve_store_prices(store, source_kind="tawreed").purchase_price
    return price if price is not None and math.isfinite(price) and price > 0 else None

def _empty_selection_reason(
    stores: list[dict[str, Any]], min_discount_percent: float
) -> str:
    available = [
        choice
        for choice in _all_store_choices(stores, [])
        if choice.available_quantity > 0
    ]
    if not available:
        return "All available stores for this product are out of stock."
    if min_discount_percent > 0 and not any(
        choice.discount_percent >= min_discount_percent - 0.001
        for choice in available
    ):
        return f"No available store meets the minimum discount {min_discount_percent:g}%."
    return "No available store has a structured purchase price."

def _normalize_store_name(name: str) -> str:
    """Normalize store name for fuzzy matching."""
    return normalize_arabic(name).casefold()

def _stores_match(name1: str, name2: str) -> bool:
    """Check if two store names match using fuzzy logic."""
    n1, n2 = _normalize_store_name(name1), _normalize_store_name(name2)
    return n1 == n2 or n1 in n2 or n2 in n1

def calculate_warehouse_priority_score(
    store_name_value: str, preferred_list: list[str]
) -> int:
    """Calculate priority score. 1=highest, 999=unknown."""
    for index, preferred_name in enumerate(preferred_list, start=1):
        if _stores_match(store_name_value, preferred_name):
            return index
    return 999
