"""Subprocess entry points for item-level parallel workers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

def run_order_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    """Process one chunk of order items in an isolated subprocess."""
    from ..core.utils.excel import Item

    profile_key, bot = _build_worker_bot(payload)
    items = [Item(code=r[0], name=r[1], qty=r[2]) for r in payload["items"]]
    return _execute_order(bot, items, profile_key)


def run_cart_removal_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    """Process one chunk of cart-removal items in an isolated subprocess."""
    from ..core.cart_removal_items import CartRemovalItem

    profile_key, bot = _build_worker_bot(payload)
    items = [CartRemovalItem(code=r[0], name=r[1]) for r in payload["items"]]
    return _execute_cart_removal(bot, items, profile_key)


def _build_worker_bot(payload: dict[str, Any]):
    """Reconstruct config, profile, and bot from the serialized payload."""
    from ..core.config.config import load_config
    from .cli_shared import build_bot

    config = load_config(Path(payload["config_path"]))
    profile_key = payload["profile_key"]
    options = payload.get("options", {})
    _apply_warehouse_overrides(config, options)
    bot = build_bot(
        config,
        profile_key,
        config.profiles[profile_key],
        **_build_bot_options(options, payload["worker_id"]),
    )
    return profile_key, bot


def _build_bot_options(options: dict[str, Any], worker_id: int) -> dict[str, Any]:
    """Return keyword arguments used to build one worker bot."""
    return {
        "debug_browser": options.get("debug_browser", False),
        "stop_flag_path": _opt_path(options.get("stop_flag")),
        "fast_search": options.get("fast_search", False),
        "summary_label_suffix": f"worker_{worker_id}",
    }


def _execute_order(bot, items, profile_key) -> dict[str, Any]:
    """Run the order flow and return a structured result."""
    from ..tawreed.tawreed_session import SessionInvalidError

    try:
        bot.place_order_from_items(iter(items))
        return {"status": "ok", "profile_key": profile_key}
    except SessionInvalidError as err:
        return {
            "status": "session_invalid",
            "profile_key": profile_key,
            "error": str(err),
        }
    except Exception as err:
        return {"status": "error", "profile_key": profile_key, "error": str(err)}


def _execute_cart_removal(bot, items, profile_key) -> dict[str, Any]:
    """Run the cart-removal flow and return a structured result."""
    from ..tawreed.tawreed_session import SessionInvalidError

    try:
        bot.remove_cart_items(iter(items))
        return {"status": "ok", "profile_key": profile_key}
    except SessionInvalidError as err:
        return {
            "status": "session_invalid",
            "profile_key": profile_key,
            "error": str(err),
        }
    except Exception as err:
        return {"status": "error", "profile_key": profile_key, "error": str(err)}


def _apply_warehouse_overrides(config, options: dict) -> None:
    """Apply warehouse-mode overrides from CLI options to config."""
    wh_mode = options.get("warehouse_mode")
    if wh_mode:
        config.warehouse_strategy["mode"] = str(wh_mode)
    min_discount = options.get("min_discount_percent")
    if min_discount is not None:
        config.warehouse_strategy["min_discount_percent"] = float(min_discount)


def _opt_path(value: str | None) -> Path | None:
    """Convert an optional string path to a Path object."""
    return Path(value) if value else None
