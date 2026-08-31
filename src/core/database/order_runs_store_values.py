"""Price, discount, and quantity extraction for store snapshot rows.

Reuses the Tawreed pricing helpers the ordering strategy already relies on, so
a stored discount always equals the discount the strategy compared against.
"""

from __future__ import annotations

from typing import Any, Iterable

from ..matching.candidate_identity import candidate_store_product_id
from .order_runs_values import as_int, as_optional_float

SYNTHETIC_ID_PREFIX = "dom-row-"
PUBLIC_PRICE_KEYS = ("retailPrice", "publicPrice", "price", "sellingPrice")
PURCHASE_PRICE_KEYS = ("salePrice", "salesPrice")


def store_price_fields(store: dict[str, Any]) -> dict[str, Any]:
    """Return the price, discount, and currency fields for one store row.

    ``public_price`` is the retail price and ``purchase_price`` is what the
    pharmacy actually pays. The CSV artifacts name these two the other way
    round (``winner_sale_price`` holds the retail price); the database uses the
    accurate names on purpose.
    """
    return {
        "public_price": _first_price(store, PUBLIC_PRICE_KEYS),
        "purchase_price": _first_price(store, PURCHASE_PRICE_KEYS),
        "discount_percent": discount_percent_value(store),
        "currency": str(store.get("currency") or "").strip(),
    }


def discount_percent_value(store: dict[str, Any]) -> float:
    """Return the store discount as a percentage, using the shared parser."""
    from ...tawreed.store.tawreed_pricing import (
        discount_value_as_percent,
        first_discount_value,
    )

    return max(0.0, discount_value_as_percent(first_discount_value(store)))


def ordered_quantity_by_product(
    selections: Iterable[tuple[dict[str, Any], int]],
) -> dict[str, int]:
    """Return ordered quantity summed per orderable product id.

    Summed rather than assigned because one store can be selected twice when a
    requested quantity is split across several passes.
    """
    totals: dict[str, int] = {}
    for store, quantity in selections or []:
        product_id = candidate_store_product_id(store)
        if not product_id:
            continue
        totals[product_id] = totals.get(product_id, 0) + as_int(quantity)
    return totals


def is_synthetic_product_id(product_id: str) -> bool:
    """Return whether an id is a DOM-fallback placeholder, not a Tawreed id."""
    return str(product_id or "").startswith(SYNTHETIC_ID_PREFIX)


def _first_price(store: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    """Return the first parseable price for the given keys, else ``None``."""
    for key in keys:
        value = as_optional_float(store.get(key))
        if value is not None:
            return value
    return None


__all__ = [
    "SYNTHETIC_ID_PREFIX",
    "PUBLIC_PRICE_KEYS",
    "PURCHASE_PRICE_KEYS",
    "store_price_fields",
    "discount_percent_value",
    "ordered_quantity_by_product",
    "is_synthetic_product_id",
]
