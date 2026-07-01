"""Multi-store operations for Tawreed API flow."""

from __future__ import annotations

from src.core.utils.excel import Item
from .tawreed_api_client import TawreedApiClient


def _add_multi_store_item_api(bot, api: TawreedApiClient, match, item: Item, record_timing) -> None:
    """Order from multiple stores natively using the API payload."""
    from ..store.tawreed_store_selection import choose_next_store_for_remaining_quantity
    from ..products.tawreed_products_flow import _wh_mode, _min_disc, _preferred_warehouses
    
    store_rows = api.get_store_details(match.data.get("productId") or match.data.get("id"))
    if not store_rows:
        raise bot.skip_item_exception("API multi-store returned no stores.")
    
    mode = _wh_mode(bot)
    max_discount_value = _validate_max_discount_if_needed(bot, mode, store_rows)
    
    sels = _select_stores_and_add_to_cart(
        bot, api, item, store_rows, mode, max_discount_value, 
        _preferred_warehouses(bot), record_timing
    )
    
    _finalize_multi_store_order(bot, sels)


def _validate_max_discount_if_needed(bot, mode, store_rows):
    """Validate max discount meets minimum requirement if in max_discount mode."""
    from ..products.tawreed_products_flow import _find_max_discount, _min_disc
    
    if mode != "max_discount" or not store_rows:
        return None
    
    max_discount_value = _find_max_discount(store_rows)
    min_discount = _min_disc(bot)
    if max_discount_value < min_discount - 0.001:
        raise bot.skip_item_exception(
            f"Highest discount ({max_discount_value:g}%) is below minimum ({min_discount:g}%)."
        )
    return max_discount_value


def _select_stores_and_add_to_cart(
    bot, api, item, store_rows, mode, max_discount_value,
    preferred_warehouses, record_timing
):
    """Select stores and add items to cart until quantity is fulfilled."""
    from ..store.tawreed_store_selection import choose_next_store_for_remaining_quantity
    from ..products.tawreed_products_flow import _effective_min_discount
    
    rem, used_ids, sels = int(item.qty), set(), []
    while rem > 0:
        choice = choose_next_store_for_remaining_quantity(
            store_rows, used_ids, mode, bot.skip_item_exception,
            _effective_min_discount(bot, sels), preferred_warehouses
        )
        if not choice or min(rem, choice.available_quantity) <= 0:
            break
        ordered = min(rem, choice.available_quantity)
        _add_store_to_cart(api, choice, ordered, bot, record_timing)
        sels.append((choice.store, ordered))
        used_ids.add(choice.identity)
        rem -= ordered
        if _should_stop_in_max_discount_mode(mode, max_discount_value, choice):
            break
    return sels


def _add_store_to_cart(api, choice, ordered, bot, record_timing):
    """Add a single store to cart and record timing."""
    import time
    cart_start = time.perf_counter()
    api.add_to_cart(choice.store, ordered)
    record_timing(bot, "add_to_cart_seconds", time.perf_counter() - cart_start)


def _should_stop_in_max_discount_mode(mode, max_discount_value, choice):
    """Check if we should stop adding more stores in max_discount mode."""
    if mode == "max_discount" and max_discount_value is not None:
        if choice.discount_percent < max_discount_value - 0.5:
            return True
    return False


def _finalize_multi_store_order(bot, sels):
    """Finalize multi-store order and record stores."""
    from ..products.tawreed_products_flow import _record_stores
    
    if not sels:
        raise bot.skip_item_exception("All stores out of stock.")
    bot.last_ordered_total_qty = sum(q for _, q in sels)
    _record_stores(bot, sels)


__all__ = [
    "_add_multi_store_item_api",
    "_validate_max_discount_if_needed",
    "_select_stores_and_add_to_cart",
    "_add_store_to_cart",
    "_should_stop_in_max_discount_mode",
    "_finalize_multi_store_order",
]
