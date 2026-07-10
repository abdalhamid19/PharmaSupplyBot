"""Main API flow functions for Tawreed."""

from __future__ import annotations

import time
from typing import Iterable

from src.core.utils.excel import Item
from .tawreed_api_client import TawreedApiClient
from .tawreed_api_contract import TawreedApiUnavailable


def match_items_only_with_api(bot, items: Iterable[Item]) -> None:
    """Match items through Tawreed API without opening Chromium."""
    with TawreedApiClient(bot.config.base_url, bot.state_path) as api:
        _require_contract(api, "product_search_url")
        _warm_up_api_client(bot, api)
        for item in items:
            if bot._stop_before_item(item):
                return
            started_at = time.perf_counter()
            bot._reset_last_item_state()
            try:
                from .tawreed_api_flow_matching import require_api_match
                from .tawreed_api_match_only_metadata import (
                    record_api_match_only_store_metadata,
                )
                match = require_api_match(bot, api, item, False)
                bot.log(f"API match-only accepted {item.code} / {item.name}: {match.query}")
                record_api_match_only_store_metadata(bot, api, match)
                
                bot.order_flow.summary_recorder.record_match_only_success(item, started_at)
            except bot.skip_item_exception as error:
                bot.order_flow.summary_recorder.record_match_only_skip(item, error, started_at)


def place_order_with_api(bot, items: Iterable[Item]) -> None:
    """Add items to Tawreed cart through discovered API endpoints."""
    with TawreedApiClient(bot.config.base_url, bot.state_path) as api:
        _require_contract(api, "product_search_url", "add_to_cart_url")
        if bot.config.runtime.submit_order:
            _require_contract(api, "submit_order_url")
        _warm_up_api_client(bot, api)
        from .tawreed_api_flow_cart import _add_api_order_items, _submit_order_if_enabled
        added_any = _add_api_order_items(bot, api, items)
        _submit_order_if_enabled(bot, api, added_any)


def remove_cart_items_with_api(bot, items: Iterable[object]) -> None:
    """Remove requested cart items through discovered API endpoints."""
    with TawreedApiClient(bot.config.base_url, bot.state_path) as api:
        _require_contract(api, "remove_cart_url")
        _warm_up_api_client(bot, api)
        for item in items:
            if bot._stop_requested():
                return
            api.remove_cart_item(item)


def _require_contract(api: TawreedApiClient, *fields: str) -> None:
    """Raise before item iteration when the discovered contract is incomplete."""
    missing = [field for field in fields if not api.contract_field_available(field)]
    if missing:
        raise TawreedApiUnavailable(f"Missing Tawreed API contract fields: {missing}")


def _warm_up_api_client(bot, api: TawreedApiClient) -> None:
    """Open the API request context once before per-item timing starts."""
    from ..matching.tawreed_timing import record_timing
    started_at = time.perf_counter()
    api.warm_up()
    elapsed = time.perf_counter() - started_at
    if hasattr(bot, "_record_pending_item_timing"):
        bot._record_pending_item_timing("api_context_init_seconds", elapsed)


__all__ = [
    "match_items_only_with_api",
    "place_order_with_api",
    "remove_cart_items_with_api",
    "_require_contract",
    "_warm_up_api_client",
]
