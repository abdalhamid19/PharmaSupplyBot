"""Bridge run-scoped Excel data and the shared Tawreed allocation policy."""

from __future__ import annotations

from typing import Any, Sequence

from src.core.ordering.excel_target_cart_gate import ExcelTargetCartGate
from src.core.ordering.warehouse_order_policy import (
    AllocationPlan,
    plan_tawreed_allocations,
)
from src.core.utils.excel import Item

from .tawreed_store_run_payload import excel_target_cart_gate_run_key, persistence_options


def plan_order_allocations(
    bot,
    item: Item,
    store_rows: Sequence[dict[str, Any]],
    *,
    mode: str,
    preferred_warehouses: Sequence[str],
    min_discount_percent: float = 0.0,
) -> AllocationPlan:
    """Plan one item using the current run's Excel Target price snapshot."""
    excel_price = _excel_purchase_price(
        bot, item, store_rows, min_discount_percent
    )
    return plan_tawreed_allocations(
        item.qty,
        store_rows,
        mode=mode,
        preferred_warehouses=preferred_warehouses,
        min_discount_percent=min_discount_percent,
        excel_purchase_price=excel_price,
    )


def _excel_purchase_price(
    bot,
    item: Item,
    tawreed_stores: Sequence[dict[str, Any]],
    min_discount_percent: float,
) -> float | None:
    """Return the lowest persisted Excel purchase price when the gate is on."""
    if getattr(bot, "match_only", False):
        return None
    run_key = excel_target_cart_gate_run_key(bot)
    if not run_key:
        return None
    options = persistence_options(bot) or {}
    if not options.get("enabled", True):
        return None
    decision = ExcelTargetCartGate(options.get("path")).evaluate_candidates(
        run_key,
        item,
        list(tawreed_stores),
        min_discount_percent=min_discount_percent,
    )
    return decision.excel_purchase_price


__all__ = ["plan_order_allocations"]
