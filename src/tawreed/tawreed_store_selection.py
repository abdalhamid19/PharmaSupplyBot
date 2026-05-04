"""Store selection and discount calculation for Tawreed orders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STORE_NAME_KEYS = (
    "storeName", "storeNameAr", "storeNameEn", "supplierName", "supplierNameAr",
    "supplierNameEn", "warehouseName", "warehouseNameAr", "warehouseNameEn",
    "pharmacyName", "branchName", "sellerName", "companyName",
)
NESTED_STORE_KEYS = ("store", "supplier", "warehouse", "pharmacy", "branch", "seller")
NESTED_NAME_KEYS = ("name", "nameAr", "nameEn", "arabicName", "englishName", "title")
DISCOUNT_KEYS = (
    "discountPercent", "discountPercentage", "discountRate", "discountValue",
    "discount", "cashDiscount", "companyDiscount", "offerDiscount",
    "pharmacyDiscount", "percentage", "percent",
)


@dataclass(frozen=True)
class StoreChoice:
    """One precomputed store candidate for split-quantity selection."""

    index: int
    store: dict[str, Any]
    identity: str
    available_quantity: int
    discount_percent: float


def choose_next_store_for_remaining_quantity(
    stores: list[dict[str, Any]],
    remaining_qty: int,
    min_discount_percent: float = 0.0,
) -> StoreChoice | None:
    """Select the best available store based on discount and availability."""
    choices = _resolve_store_choices(stores)
    valid_choices = [
        c for c in choices
        if c.available_quantity > 0 and c.discount_percent >= min_discount_percent
    ]
    if not valid_choices:
        return None

    # Sorting logic (Strategy)
    # For now, default to first available or highest discount
    # Let's assume highest discount for now as a common strategy
    valid_choices.sort(key=lambda c: c.discount_percent, reverse=True)
    return valid_choices[0]


def _resolve_store_choices(stores: list[dict[str, Any]]) -> list[StoreChoice]:
    """Map raw store API objects into a list of comparable StoreChoice objects."""
    choices: list[StoreChoice] = []
    for index, store in enumerate(stores):
        choices.append(_store_choice(index, store))
    return choices


def _store_choice(index: int, store: dict[str, Any]) -> StoreChoice:
    """Create a single StoreChoice from a raw store dictionary."""
    return StoreChoice(
        index=index,
        store=store,
        identity=_store_name(store),
        available_quantity=int(store.get("availableQuantity", 0)),
        discount_percent=_first_discount_value(store),
    )


def _store_name(store: dict[str, Any]) -> str:
    """Extract a human-readable name for the store from various possible API keys."""
    for key in STORE_NAME_KEYS:
        if store.get(key):
            return str(store[key])
    for nested_key in NESTED_STORE_KEYS:
        nested = store.get(nested_key)
        if isinstance(nested, dict):
            for name_key in NESTED_NAME_KEYS:
                if nested.get(name_key):
                    return str(nested[name_key])
    return "Unknown Store"


def _first_discount_value(store: dict[str, Any]) -> float:
    """Extract the primary discount percentage value from the store API data."""
    for key, value in store.items():
        if _is_discount_key(key):
            discount = _discount_value(value)
            if discount > 0:
                return discount
    return 0.0


def _discount_value(value: Any) -> float:
    """Parse a discount value into a float percentage."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _is_discount_key(key: str) -> bool:
    """Return whether the provided key likely represents a discount percentage."""
    k = key.lower()
    return any(dk.lower() in k for dk in DISCOUNT_KEYS)


def _is_name_key(key: str) -> bool:
    """Return whether the provided key likely represents a store or product name."""
    k = key.lower()
    return "name" in k or "title" in k
