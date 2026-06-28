"""Utility functions for Tawreed API flow."""

import time
from typing import Iterable

from .tawreed_api import TawreedApiClient


def remove_cart_items_with_api(bot, items: Iterable[object]) -> None:
    """Remove requested cart items through discovered API endpoints."""
    with TawreedApiClient(bot.config.base_url, bot.state_path) as api:
        _require_contract(api, "remove_cart_url")
        _warm_up_api_client(bot, api)
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


def _warm_up_api_client(bot, api: TawreedApiClient) -> None:
    """Open the API request context once before per-item timing starts."""
    started_at = time.perf_counter()
    api.warm_up()
    elapsed = time.perf_counter() - started_at
    if hasattr(bot, "_record_pending_item_timing"):
        bot._record_pending_item_timing("api_context_init_seconds", elapsed)
