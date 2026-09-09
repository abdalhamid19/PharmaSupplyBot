"""Cart operations for Tawreed API flow."""

from __future__ import annotations

import logging
import time
from typing import Iterable

from src.core.ordering.excel_target_cart_gate import ExcelTargetCartGate
from src.core.utils.excel import Item
from .tawreed_api_client import TawreedApiClient


logger = logging.getLogger(__name__)


def _raise_if_excel_target_cart_blocked(bot, item: Item, tawreed_store: dict) -> None:
    """Stop a real API cart mutation when Excel Target is cheaper or equal."""
    if getattr(bot, "match_only", False):
        return

    from ..store.tawreed_store_run_payload import excel_target_cart_gate_run_key

    run_key = excel_target_cart_gate_run_key(bot)
    if not run_key:
        return
    database = getattr(getattr(bot, "config", None), "database", None)
    options_factory = getattr(database, "persistence_options", None)
    if callable(options_factory):
        database_options = options_factory()
        if not database_options.get("enabled", True):
            return
        db_path = database_options.get("path")
    else:
        if database is not None and not getattr(database, "order_runs_enabled", True):
            return
        db_path = getattr(database, "order_runs_path", "") or None
    decision = ExcelTargetCartGate(db_path).evaluate(run_key, item, tawreed_store)
    if decision.blocked:
        raise bot.skip_item_exception(decision.reason)


def _add_api_order_items(bot, api: TawreedApiClient, items: Iterable[Item]) -> bool:
    """Add every requested item through the API and record summaries."""
    from ..matching.tawreed_timing import record_timing
    
    added_any = False
    for item in items:
        if bot._stop_before_item(item):
            return added_any
        started_at = time.perf_counter()
        bot._reset_last_item_state()
        try:
            _add_single_api_item(bot, api, item, record_timing)
            bot.order_flow.summary_recorder.record_success(item, started_at)
            added_any = True
        except bot.skip_item_exception as error:
            bot.order_flow.summary_recorder.record_skip(item, error, started_at)
    return added_any


def _add_single_api_item(bot, api, item, record_timing):
    """Add a single item via API."""
    from .tawreed_api_flow_matching import require_api_match

    match = require_api_match(bot, api, item, True)
    has_product_id = bool(match.data.get("productId") or match.data.get("id"))
    is_multi = int(match.data.get("productsCount") or 0) > 0 and has_product_id
    if is_multi:
        from .tawreed_api_flow_multistore import _add_multi_store_item_api
        _add_multi_store_item_api(bot, api, match, item, record_timing)
        return
    _add_single_item_to_cart(bot, api, match, item, record_timing)
    _record_single_store_item(bot, match, item)


def _record_single_store_item(bot, match, item) -> None:
    """Record store metadata for a product supplied by exactly one store.

    Single-store products never open the stores dialog, so the search row is the
    only record of the store that supplied them.
    """
    from ..store.tawreed_store_summary import record_single_store
    from ..store.tawreed_store_snapshot import (
        SOURCE_SEARCH_ROW,
        record_store_rows,
        record_store_selections,
    )

    record_single_store(bot, match.data)
    record_store_rows(bot, [match.data], SOURCE_SEARCH_ROW)
    record_store_selections(bot, [(match.data, int(item.qty))])


def _add_single_item_to_cart(bot, api, match, item, record_timing):
    """Execute add-to-cart API call and record timing."""
    from src.core.matching.candidate_identity import candidate_has_store_product_id
    from ..products.tawreed_products_flow import _min_disc
    from ..store.tawreed_pricing import discount_value_as_percent, first_discount_value

    if not candidate_has_store_product_id(match.data):
        raise bot.skip_item_exception(
            f"Matched product is not orderable (missing storeProductId) "
            f"for '{item.name}'."
        )

    min_discount = _min_disc(bot)
    if min_discount > 0:
        store_discount = discount_value_as_percent(first_discount_value(match.data))
        if store_discount < min_discount - 0.001:
            raise bot.skip_item_exception(
                f"Store discount ({store_discount:g}%) is below minimum ({min_discount:g}%)."
            )

    _raise_if_excel_target_cart_blocked(bot, item, match.data)
    cart_start = time.perf_counter()
    try:
        api.add_to_cart(match, int(item.qty))
    except ValueError as error:
        # Defense in depth: never let empty/invalid storeProductId crash the run.
        message = str(error)
        if "storeProductId" in message:
            raise bot.skip_item_exception(message) from error
        raise
    record_timing(bot, "add_to_cart_seconds", time.perf_counter() - cart_start)
    bot.last_ordered_total_qty = int(item.qty)


def _submit_order_if_enabled(bot, api: TawreedApiClient, added_any: bool) -> None:
    if not added_any or bot._stop_requested():
        logger.info(
            "order confirmation skipped (stop requested or no items added)",
            extra={"profile": bot.profile_key},
        )
        return
    if getattr(bot, "match_only", False):
        logger.info(
            "order submission skipped (match-only run)",
            extra={"profile": bot.profile_key},
        )
        return
    if not bot.config.runtime.submit_order:
        logger.info(
            "order submission disabled by config",
            extra={"profile": bot.profile_key},
        )
        return
    api.submit_order()


__all__ = [
    "_add_api_order_items",
    "_add_single_api_item",
    "_add_single_item_to_cart",
    "_raise_if_excel_target_cart_blocked",
    "_record_single_store_item",
    "_submit_order_if_enabled",
]
