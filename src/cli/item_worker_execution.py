"""Execution helpers for item-level worker subprocesses."""

from __future__ import annotations

from typing import Any

from ..tawreed.tawreed_session import SessionInvalidError


def execute_order_worker(bot, items, profile_key: str) -> dict[str, Any]:
    """Run the order or match-only worker flow and return a structured result."""
    try:
        _execute_order_or_match_only(bot, iter(items))
        return {"status": "ok", "profile_key": profile_key}
    except SessionInvalidError as err:
        return _worker_error_result("session_invalid", profile_key, err)
    except Exception as err:
        return _worker_error_result("error", profile_key, err)


def execute_cart_removal_worker(bot, items, profile_key: str) -> dict[str, Any]:
    """Run the cart-removal worker flow and return a structured result."""
    try:
        bot.remove_cart_items(iter(items))
        return {"status": "ok", "profile_key": profile_key}
    except SessionInvalidError as err:
        return _worker_error_result("session_invalid", profile_key, err)
    except Exception as err:
        return _worker_error_result("error", profile_key, err)


def _execute_order_or_match_only(bot, items) -> None:
    """Run the worker's selected order mode."""
    if getattr(bot, "match_only", False):
        bot.match_items_only(items)
        return
    bot.place_order_from_items(items)


def _worker_error_result(
    status: str, profile_key: str, err: Exception
) -> dict[str, Any]:
    """Return a standard worker error payload."""
    return {"status": status, "profile_key": profile_key, "error": str(err)}
