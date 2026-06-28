"""Main API-backed Tawreed execution flows (deprecated - functionality moved to tawreed_api_flow.py)."""

from __future__ import annotations

import time
from typing import Iterable

from ..core.utils.excel import Item
from .tawreed_api_client import TawreedApiClient
from .tawreed_api_flow import require_api_match, _require_contract, _warm_up_api_client


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
                match = require_api_match(bot, api, item, False)
                bot.log(f"API match-only accepted {item.code} / {item.name}: {match.query}")
                
                from .tawreed_store_summary import record_single_store
                record_single_store(bot, getattr(match, "data", {}))
                
                bot.order_flow.summary_recorder.record_match_only_success(item, started_at)
            except bot.skip_item_exception as error:
                bot.order_flow.summary_recorder.record_match_only_skip(item, error, started_at)
