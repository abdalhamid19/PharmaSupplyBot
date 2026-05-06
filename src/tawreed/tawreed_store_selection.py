"""Store selection and discount calculation for Tawreed orders."""
from __future__ import annotations

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


def available_store_choices(
    stores: list[dict[str, Any]],
    used_store_ids: set[str] | None = None,
    min_discount_percent: float = 0.0,
) -> list[StoreChoice]:
    """Return unused stores that have stock and satisfy the minimum discount."""
    used_ids = used_store_ids or set()
    return [
        choice
        for choice in _all_store_choices(stores)
        if choice.identity not in used_ids
        if choice.available_quantity > 0
        if choice.discount_percent >= min_discount_percent
    ]


def choose_next_store_for_remaining_quantity(
    stores: list[dict[str, Any]],
    used_store_ids: set[str] | None = None,
    mode: str = "first_available",
    skip_exception_cls: type[Exception] = RuntimeError,
    min_discount_percent: float = 0.0,
) -> StoreChoice | None:
    """Choose the next store for a remaining item quantity."""
    choices = available_store_choices(stores, used_store_ids, min_discount_percent)
    if choices:
        return _select_choice(choices, mode)
    if available_store_choices(stores, None, min_discount_percent):
        return None
    raise skip_exception_cls(_empty_selection_reason(min_discount_percent))


def _select_choice(choices: list[StoreChoice], mode: str) -> StoreChoice:
    if mode == "first_available":
        return choices[0]
    if mode == "max_available":
        return max(choices, key=lambda c: (c.available_quantity, c.discount_percent))
    if mode == "max_discount":
        return max(choices, key=lambda c: (c.discount_percent, c.available_quantity))
    raise ValueError(f"Unknown warehouse strategy mode: {mode}")


def _all_store_choices(stores: list[dict[str, Any]]) -> list[StoreChoice]:
    return [_store_choice(index, store) for index, store in enumerate(stores)]


def _store_choice(index: int, store: dict[str, Any]) -> StoreChoice:
    return StoreChoice(
        index=index,
        store=store,
        identity=_store_identity(index, store),
        available_quantity=_available_quantity(store),
        discount_percent=_discount_percent(store),
    )


def _store_identity(index: int, store: dict[str, Any]) -> str:
    for key in ("storeProductId", "productStoreId", "storeId", "supplierId", "id"):
        value = str(store.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    return f"storeName:{store_name(store)}:{index}"


def _available_quantity(store: dict[str, Any]) -> int:
    try:
        return int(float(str(store.get("availableQuantity") or 0).replace(",", "")))
    except (TypeError, ValueError):
        return 0


def _discount_percent(store: dict[str, Any]) -> float:
    return max(0.0, discount_value_as_percent(first_discount_value(store)))


def _empty_selection_reason(min_discount_percent: float) -> str:
    if min_discount_percent > 0:
        return f"No available store meets minimum discount {min_discount_percent:g}%."
    return "All available stores for this product are out of stock."
