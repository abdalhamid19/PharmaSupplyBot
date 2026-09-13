"""Shared Excel Target gate and Tawreed allocation policy.

The policy is deliberately side-effect free.  It decides whether a Tawreed
item is deferred to Excel Target and, when it is not, how the requested
quantity is allocated across Tawreed offers.  Cart mutation and persistence
belong to the calling order flow.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

from ..pricing import resolve_store_prices
from ..pricing.price_comparison import PURCHASE_PRICE_TOLERANCE_EGP
from ..normalization.normalizer import normalize_arabic
from ..config.config_models import LOWEST_PURCHASE_PRICE_MODE
from ...tawreed.store.tawreed_pricing import (
    discount_value_as_percent,
    first_discount_value,
)
from ...tawreed.store.tawreed_store_summary import store_name


PRICE_TOLERANCE_EGP = PURCHASE_PRICE_TOLERANCE_EGP


@dataclass(frozen=True)
class AllocationLine:
    """One Tawreed store allocation in the planned order."""

    store: dict[str, Any]
    quantity: int
    reason: str


@dataclass(frozen=True)
class AllocationPlan:
    """Pure result of applying the shared order policy to one item."""

    blocked_by_excel_target: bool
    excel_purchase_price: float | None
    tawreed_reference_price: float | None
    reason: str
    allocations: tuple[AllocationLine, ...]
    remaining_qty: int


def plan_tawreed_allocations(
    requested_qty: int,
    tawreed_offers: Sequence[dict[str, Any]],
    *,
    mode: str = LOWEST_PURCHASE_PRICE_MODE,
    preferred_warehouses: Sequence[str] = (),
    min_discount_percent: float = 0.0,
    excel_offers: Sequence[dict[str, Any]] = (),
    excel_purchase_price: float | None = None,
) -> AllocationPlan:
    """Apply the Excel gate and allocate one Tawreed item.

    Offers must have positive stock, a valid purchase price, and a discount at
    least ``min_discount_percent`` regardless of source. Purchase price is the
    primary ordering rule. The configured warehouse order applies only among
    offers with the same exact price.
    Once a store's stock is used, allocation continues to the next-lowest price.

    Excel Target is a source-level alternative, not a Tawreed allocation.  A
    valid Excel purchase price less than 0.25 EGP above the Tawreed reference
    blocks the whole Tawreed item and returns no allocations.
    """
    if mode != LOWEST_PURCHASE_PRICE_MODE:
        raise ValueError(
            "Only lowest_purchase_price is supported for warehouse selection"
        )
    requested = max(0, int(requested_qty))
    if requested == 0:
        return AllocationPlan(False, None, None, "empty_request", (), 0)

    minimum_discount = max(0.0, _number(min_discount_percent) or 0.0)
    tawreed = _eligible_offers(
        tawreed_offers,
        source_kind="tawreed",
        min_discount_percent=minimum_discount,
    )
    excel = _eligible_offers(
        excel_offers,
        source_kind="excel_target",
        min_discount_percent=minimum_discount,
    )
    excel_price = (
        _number(excel_purchase_price)
        if excel_purchase_price is not None
        else min((offer["purchase_price"] for offer in excel), default=None)
    )
    tawreed_price = min(
        (offer["purchase_price"] for offer in tawreed), default=None
    )

    if (
        excel_price is not None
        and tawreed_price is not None
        and excel_price < tawreed_price + PRICE_TOLERANCE_EGP
    ):
        return AllocationPlan(
            True,
            excel_price,
            tawreed_price,
            "deferred_to_excel_target",
            (),
            requested,
        )

    if not tawreed:
        if excel_price is not None:
            return AllocationPlan(
                True,
                excel_price,
                None,
                "deferred_to_excel_target",
                (),
                requested,
            )
        return AllocationPlan(
            False,
            excel_price,
            tawreed_price,
            "no_eligible_tawreed_offer",
            (),
            requested,
        )

    ordered_offers = _preference_ordered_offers(tawreed, preferred_warehouses)

    allocations: list[AllocationLine] = []
    remaining = requested
    for offer in ordered_offers:
        if remaining <= 0:
            break
        quantity = min(remaining, offer["available_qty"])
        if quantity <= 0:
            continue
        allocations.append(
            AllocationLine(
                store=offer["store"],
                quantity=quantity,
                reason=LOWEST_PURCHASE_PRICE_MODE,
            )
        )
        remaining -= quantity

    return AllocationPlan(
        False,
        excel_price,
        tawreed_price,
        "allocated" if allocations else "no_eligible_tawreed_offer",
        tuple(allocations),
        remaining,
    )


def excel_target_blocks_tawreed(
    excel_purchase_price: float | None,
    tawreed_purchase_price: float | None,
) -> bool:
    """Return whether an Excel price diverts the item from Tawreed."""
    return (
        excel_purchase_price is not None
        and tawreed_purchase_price is not None
        and excel_purchase_price < tawreed_purchase_price + PRICE_TOLERANCE_EGP
    )


def _eligible_offers(
    offers: Sequence[dict[str, Any]],
    *,
    source_kind: str,
    min_discount_percent: float = 0.0,
) -> list[dict[str, Any]]:
    eligible: list[dict[str, Any]] = []
    for offer in offers:
        available = _available_quantity(offer)
        price = _purchase_price(offer, source_kind)
        discount = _discount_percent(offer)
        if available <= 0 or price is None or price <= 0:
            continue
        if not math.isfinite(price) or discount < float(min_discount_percent) - 0.001:
            continue
        eligible.append(
            {
                "store": offer,
                "available_qty": available,
                "purchase_price": price,
                "discount_percent": discount,
                "store_name": str(offer.get("store_name") or store_name(offer)),
            }
        )
    return eligible


def _preference_ordered_offers(
    offers: Sequence[dict[str, Any]],
    preferred_warehouses: Sequence[str],
) -> list[dict[str, Any]]:
    """Order by purchase price, then preference among exact-price ties."""
    return sorted(
        offers,
        key=lambda offer: (
            offer["purchase_price"],
            _warehouse_rank(offer["store_name"], preferred_warehouses),
            _stable_offer_key(offer),
        ),
    )


def _purchase_price(offer: dict[str, Any], source_kind: str) -> float | None:
    direct = _number(offer.get("purchase_price"))
    if direct is not None:
        return direct
    resolved = resolve_store_prices(
        offer,
        source_kind="excel_target" if source_kind == "excel_target" else "tawreed",
    )
    return resolved.purchase_price


def _available_quantity(offer: dict[str, Any]) -> int:
    value = offer.get("available_qty", offer.get("availableQuantity", 0))
    number = _number(value)
    return max(0, int(number or 0))


def _discount_percent(offer: dict[str, Any]) -> float:
    direct = _number(offer.get("discount_percent"))
    if direct is not None:
        return max(0.0, direct)
    return max(0.0, discount_value_as_percent(first_discount_value(offer)))


def _number(value: Any) -> float | None:
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _warehouse_rank(name: str, preferred: Sequence[str]) -> int:
    normalized = _normalize(name)
    for index, preferred_name in enumerate(preferred):
        candidate = _normalize(preferred_name)
        if normalized == candidate or normalized in candidate or candidate in normalized:
            return index
    return len(preferred)


def _normalize(value: str) -> str:
    return normalize_arabic(str(value or "")).casefold()


def _stable_offer_key(offer: dict[str, Any]) -> str:
    store = offer["store"]
    return str(
        store.get("storeProductId")
        or store.get("store_product_id")
        or store.get("storeId")
        or store.get("store_key")
        or offer.get("store_name")
        or ""
    )


__all__ = [
    "AllocationLine",
    "AllocationPlan",
    "LOWEST_PURCHASE_PRICE_MODE",
    "PRICE_TOLERANCE_EGP",
    "excel_target_blocks_tawreed",
    "plan_tawreed_allocations",
]
