"""Build a clearly-labeled hypothetical basket from match-only snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ....core.database.warehouse_winner_selection import PREFERRED_WAREHOUSES
from ....core.ordering.warehouse_order_policy import (
    AllocationPlan,
    LOWEST_PURCHASE_PRICE_MODE,
    plan_tawreed_allocations,
)

TAWREED_SOURCES = {"store_details", "search"}
EXCEL_SOURCES = {"excel_target", "excel-target"}


@dataclass(frozen=True)
class MatchOnlyPurchaseSimulation:
    """Hypothetical Tawreed allocations and Excel Target diversions."""

    tawreed_rows: list[dict[str, Any]]
    excel_target_rows: list[dict[str, Any]]
    manual_review_items: int
    unsupported_strategy_items: int


def build_match_only_purchase_simulation(
    rows: list[dict[str, Any]],
) -> MatchOnlyPurchaseSimulation | None:
    """Apply the order policy to one match-only run's persisted offer rows.

    The simulation only includes accepted Tawreed matches and replays them
    with the current default warehouse preferences because runs do not store
    custom preference lists. Excel Target wins are shown separately because
    they would not be added to Tawreed's basket.
    """
    if not rows or rows[0].get("run_mode") != "match-only":
        return None
    return _simulate_items(_group_by_item(rows))


def _simulate_items(
    items_by_key: dict[str, list[dict[str, Any]]],
) -> MatchOnlyPurchaseSimulation:
    tawreed_rows: list[dict[str, Any]] = []
    excel_target_rows: list[dict[str, Any]] = []
    manual_review_items = unsupported_strategy_items = 0
    for item_rows in items_by_key.values():
        item_simulation = _simulate_item_purchase(item_rows)
        tawreed_rows.extend(item_simulation.tawreed_rows)
        excel_target_rows.extend(item_simulation.excel_target_rows)
        manual_review_items += item_simulation.manual_review_items
        unsupported_strategy_items += item_simulation.unsupported_strategy_items

    return MatchOnlyPurchaseSimulation(
        tawreed_rows=tawreed_rows,
        excel_target_rows=excel_target_rows,
        manual_review_items=manual_review_items,
        unsupported_strategy_items=unsupported_strategy_items,
    )


def _simulate_item_purchase(
    item_rows: list[dict[str, Any]],
) -> MatchOnlyPurchaseSimulation:
    item_facts = item_rows[0]
    if not _accepted_tawreed_match(item_facts):
        review_count = int(bool(item_facts.get("manual_review_required")))
        return _empty_simulation(manual_review_items=review_count)
    return _simulate_accepted_item(item_rows, item_facts)


def _simulate_accepted_item(
    item_rows: list[dict[str, Any]], item_facts: dict[str, Any]
) -> MatchOnlyPurchaseSimulation:
    requested_mode = LOWEST_PURCHASE_PRICE_MODE

    tawreed_offers, excel_offers = _item_offers(item_rows)
    min_discount_percent = _number(item_facts.get("min_discount_pct")) or 0.0
    allocation_plan = plan_tawreed_allocations(
        item_facts.get("requested_qty", 0),
        tawreed_offers,
        mode=requested_mode,
        preferred_warehouses=PREFERRED_WAREHOUSES,
        min_discount_percent=min_discount_percent,
        excel_offers=excel_offers,
    )
    return _simulation_from_plan(
        item_facts, excel_offers, allocation_plan, min_discount_percent
    )


def _simulation_from_plan(
    item_facts: dict[str, Any],
    excel_offers: list[dict[str, Any]],
    allocation_plan: AllocationPlan,
    min_discount_percent: float,
) -> MatchOnlyPurchaseSimulation:
    if allocation_plan.blocked_by_excel_target:
        return _simulate_excel_target(
            item_facts, excel_offers, allocation_plan, min_discount_percent
        )
    return _simulate_tawreed_allocations(item_facts, allocation_plan)


def _empty_simulation(
    *, manual_review_items: int = 0, unsupported_strategy_items: int = 0
) -> MatchOnlyPurchaseSimulation:
    return MatchOnlyPurchaseSimulation(
        tawreed_rows=[],
        excel_target_rows=[],
        manual_review_items=manual_review_items,
        unsupported_strategy_items=unsupported_strategy_items,
    )


def _item_offers(
    item_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tawreed_offers = [
        row for row in item_rows
        if row.get("source") in TAWREED_SOURCES and row.get("store_product_id")
    ]
    excel_offers = [
        row for row in item_rows
        if row.get("source") in EXCEL_SOURCES
        and row.get("store_product_id")
        and row.get("excel_matched", 1)
        and not row.get("excel_manual_review_required", 0)
    ]
    return tawreed_offers, excel_offers


def _simulate_excel_target(
    item_facts: dict[str, Any],
    excel_offers: list[dict[str, Any]],
    allocation_plan: AllocationPlan,
    min_discount_percent: float,
) -> MatchOnlyPurchaseSimulation:
    excel_offer = _lowest_priced_offer(excel_offers, min_discount_percent)
    if excel_offer is None:
        return _empty_simulation()
    return MatchOnlyPurchaseSimulation(
        tawreed_rows=[],
        excel_target_rows=[
            _excel_target_row(
                item_facts, excel_offer, allocation_plan.excel_purchase_price
            )
        ],
        manual_review_items=0,
        unsupported_strategy_items=0,
    )


def _simulate_tawreed_allocations(
    item_facts: dict[str, Any], allocation_plan: AllocationPlan
) -> MatchOnlyPurchaseSimulation:
    allocations = [
        _tawreed_row(
            item_facts, allocation.store, allocation.quantity,
            allocation_plan.remaining_qty,
        )
        for allocation in allocation_plan.allocations
    ]
    return MatchOnlyPurchaseSimulation(
        tawreed_rows=allocations,
        excel_target_rows=[],
        manual_review_items=0,
        unsupported_strategy_items=0,
    )


def _group_by_item(
    rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item_key = str(row.get("item_key") or "")
        if item_key:
            grouped.setdefault(item_key, []).append(row)
    return grouped


def _accepted_tawreed_match(item_facts: dict[str, Any]) -> bool:
    """Reject unresolved and manual-review matches from the simulation."""
    return (
        item_facts.get("status") == "matched-only"
        and bool(item_facts.get("matched"))
        and not bool(item_facts.get("manual_review_required"))
    )


def _lowest_priced_offer(
    offers: list[dict[str, Any]],
    min_discount_percent: float = 0.0,
) -> dict[str, Any] | None:
    eligible = [
        offer for offer in offers
        if _number(offer.get("purchase_price")) is not None
        and _number(offer.get("purchase_price")) > 0
        and _number(offer.get("available_qty")) is not None
        and _number(offer.get("available_qty")) > 0
        and (_number(offer.get("discount_percent")) or 0.0)
        >= min_discount_percent - 0.001
    ]
    return min(
        eligible,
        key=lambda offer: (
            _number(offer.get("purchase_price")),
            str(offer.get("source_label") or ""),
            str(offer.get("store_product_id") or ""),
        ),
        default=None,
    )


def _tawreed_row(
    item_facts: dict[str, Any],
    offer: dict[str, Any],
    quantity: int,
    unfilled_qty: int,
) -> dict[str, Any]:
    return {
        **_item_fields(item_facts),
        "store_name": offer.get("store_name") or offer.get("store_key") or "",
        "matched_name": (
            offer.get("offer_matched_name") or item_facts.get("matched_name")
        ),
        "simulated_qty": int(quantity),
        "unfilled_qty": int(unfilled_qty),
        "available_qty": int(_number(offer.get("available_qty")) or 0),
        "public_price": _number(offer.get("public_price")),
        "purchase_price": _number(offer.get("purchase_price")),
        "discount_percent": _number(offer.get("discount_percent")),
    }


def _excel_target_row(
    item_facts: dict[str, Any],
    offer: dict[str, Any],
    purchase_price: float | None,
) -> dict[str, Any]:
    return {
        **_item_fields(item_facts),
        "excel_target_source": offer.get("source_label") or "Excel Target",
        "matched_name": (
            offer.get("offer_matched_name") or item_facts.get("matched_name")
        ),
        "simulated_qty": 1,
        "purchase_price": purchase_price,
        "discount_percent": _number(offer.get("discount_percent")),
    }


def _item_fields(item_facts: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_key": item_facts.get("item_key"),
        "item_code": item_facts.get("item_code"),
        "item_name": item_facts.get("item_name"),
        "requested_qty": int(_number(item_facts.get("requested_qty")) or 0),
    }


def _number(raw_value: Any) -> float | None:
    try:
        return float(str(raw_value).replace(",", ""))
    except (TypeError, ValueError):
        return None


__all__ = [
    "MatchOnlyPurchaseSimulation",
    "build_match_only_purchase_simulation",
]
