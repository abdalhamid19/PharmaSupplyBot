"""API-backed Tawreed execution flows with browser-compatible summaries."""

from __future__ import annotations

import time
from typing import Iterable

from ..core.utils.excel import Item
from .tawreed_api import TawreedApiClient
from .tawreed_api_matching import require_api_match


def match_items_only_with_api(bot, items: Iterable[Item]) -> None:
    """Match items through Tawreed API without opening Chromium."""
    with TawreedApiClient(bot.config.base_url, bot.state_path) as api:
        _require_contract(api, "product_search_url")
        for item in items:
            if bot._stop_before_item(item):
                return
            started_at = time.perf_counter()
            bot._reset_last_item_state()
            try:
                match = require_api_match(bot, api, item, False)
                bot.log(f"API match-only accepted {item.code} / {item.name}: {match.query}")
                bot._record_match_only_success(item, started_at)
            except bot.skip_item_exception as error:
                bot._record_match_only_skip(item, error, started_at)


def place_order_with_api(bot, items: Iterable[Item]) -> None:
    """Add items to Tawreed cart through discovered API endpoints."""
    with TawreedApiClient(bot.config.base_url, bot.state_path) as api:
        _require_contract(api, "product_search_url", "add_to_cart_url")
        if bot.config.runtime.submit_order:
            _require_contract(api, "submit_order_url")
        added_any = _add_api_order_items(bot, api, items)
        _submit_order_if_enabled(bot, api, added_any)


def _add_api_order_items(bot, api: TawreedApiClient, items: Iterable[Item]) -> bool:
    """Add every requested item through the API and record summaries."""
    added_any = False
    for item in items:
        if bot._stop_before_item(item):
            return added_any
        started_at = time.perf_counter()
        bot._reset_last_item_state()
        try:
            match = require_api_match(bot, api, item, True)
            api.add_to_cart(match, item.qty)
            bot.last_ordered_total_qty = int(item.qty)
            bot._record_success(item, started_at)
            added_any = True
        except bot.skip_item_exception as error:
            bot._record_skip(item, error, started_at)
    return added_any


def remove_cart_items_with_api(bot, items: Iterable[object]) -> None:
    """Remove requested cart items through discovered API endpoints."""
    with TawreedApiClient(bot.config.base_url, bot.state_path) as api:
        _require_contract(api, "remove_cart_url")
        for item in items:
            if bot._stop_requested():
                return
            api.remove_cart_item(item)


def _submit_order_if_enabled(bot, api: TawreedApiClient, added_any: bool) -> None:
    if not added_any or bot._stop_requested():
        print(f"[{bot.profile_key}] Stop requested or incomplete. Order confirmation skipped.")
        return
    if getattr(bot, "match_only", False):
        print(f"[{bot.profile_key}] Match-only run. Final order submission skipped.")
        return
    if not bot.config.runtime.submit_order:
        print(f"[{bot.profile_key}] Items added to cart. Final order submission is disabled.")
        return
    api.submit_order()


def _require_contract(api: TawreedApiClient, *fields: str) -> None:
    """Raise before item iteration when the discovered contract is incomplete."""
    from .tawreed_api import TawreedApiUnavailable

    missing = [field for field in fields if not api.contract_field_available(field)]
    if missing:
        raise TawreedApiUnavailable(f"Missing Tawreed API contract fields: {missing}")
