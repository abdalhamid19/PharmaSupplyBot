"""Multi-store operations for Tawreed API flow."""

from __future__ import annotations

from types import SimpleNamespace

from src.core.utils.excel import Item
from src.core.ordering.warehouse_order_policy import LOWEST_PURCHASE_PRICE_MODE
from src.tawreed.store.tawreed_order_planning import plan_order_allocations
from .tawreed_api_client import TawreedApiClient
from .tawreed_api_flow_cart import _raise_if_excel_target_cart_blocked


def _add_multi_store_item_api(bot, api: TawreedApiClient, match, item: Item, record_timing) -> None:
    """Order from multiple stores natively using the API payload."""
    from ..products.tawreed_products_flow import _min_disc, _preferred_warehouses
    from ..store.tawreed_store_snapshot import SOURCE_STORE_DETAILS, record_store_rows
    
    store_rows = api.get_store_details(match.data.get("productId") or match.data.get("id"))
    if not store_rows:
        raise bot.skip_item_exception("API multi-store returned no stores.")
    record_store_rows(bot, store_rows, SOURCE_STORE_DETAILS)
    
    sels = _select_stores_and_add_to_cart(
        bot, api, item, store_rows, _preferred_warehouses(bot), record_timing
    )
    
    _finalize_multi_store_order(bot, sels)


def _select_stores_and_add_to_cart(
    bot, api, item, store_rows, preferred_warehouses, record_timing
):
    """Select stores and add items to cart until quantity is fulfilled."""
    from ..products.tawreed_products_flow import _min_disc
    plan = plan_order_allocations(
        bot,
        item,
        store_rows,
        mode=LOWEST_PURCHASE_PRICE_MODE,
        preferred_warehouses=preferred_warehouses,
        min_discount_percent=_min_disc(bot),
    )
    if plan.blocked_by_excel_target:
        raise bot.skip_item_exception(
            f"Excel Target deferred_to_excel_target: {plan.reason}; "
            f"{plan.excel_purchase_price:.2f}"
        )
    if not plan.allocations:
        raise bot.skip_item_exception("All stores out of stock or unpriced.")

    completed_sels = []
    for line in plan.allocations:
        choice = SimpleNamespace(store=line.store)
        _add_store_to_cart(api, choice, line.quantity, bot, record_timing,
                           gate_checked=True, item=item)
        completed_sels.append((line.store, line.quantity))
        bot.last_ordered_total_qty = sum(qty for _, qty in completed_sels)
    return completed_sels


def _add_store_to_cart(
    api, choice, ordered, bot, record_timing, *, gate_checked: bool = False, item: Item | None = None
):
    """Add a single store to cart and record timing."""
    import time
    from ..products.tawreed_products_flow import _require_min_discount

    _require_min_discount(bot, choice.store)
    if not gate_checked:
        if item is None:
            raise ValueError("item is required for the Excel Target cart gate")
        _raise_if_excel_target_cart_blocked(bot, item, choice.store)
    cart_start = time.perf_counter()
    api.add_to_cart(choice.store, ordered)
    record_timing(bot, "add_to_cart_seconds", time.perf_counter() - cart_start)


def _finalize_multi_store_order(bot, sels):
    """Finalize multi-store order and record stores."""
    from ..products.tawreed_products_flow import _record_stores
    
    if not sels:
        raise bot.skip_item_exception("All stores out of stock.")
    bot.last_ordered_total_qty = sum(q for _, q in sels)
    _record_stores(bot, sels)


__all__ = [
    "_add_multi_store_item_api",
    "_select_stores_and_add_to_cart",
    "_add_store_to_cart",
    "_finalize_multi_store_order",
]
