"""Subprocess entry points for item-level parallel workers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .item_worker_execution import execute_cart_removal_worker, execute_order_worker


def run_order_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    """Process one chunk of order items in an isolated subprocess."""
    from ..core.utils.excel import Item

    profile_key, bot = _build_worker_bot(payload)
    items = [Item(code=r[0], name=r[1], qty=r[2]) for r in payload["items"]]
    with _worker_artifact_run(payload, profile_key):
        return execute_order_worker(bot, items, profile_key)


def run_cart_removal_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    """Process one chunk of cart-removal items in an isolated subprocess."""
    from ..core.cart_removal_items import CartRemovalItem

    profile_key, bot = _build_worker_bot(payload)
    items = [CartRemovalItem(code=r[0], name=r[1]) for r in payload["items"]]
    with _worker_artifact_run(payload, profile_key):
        return execute_cart_removal_worker(bot, items, profile_key)


def _worker_artifact_run(payload: dict[str, Any], profile_key: str):
    """Return a run context for subprocess artifact writes."""
    from contextlib import nullcontext
    from ..core.artifact_run import artifact_run

    options = payload.get("options", {})
    command = options.get("artifact_command")
    run_id = options.get("artifact_run_id")
    if command and run_id:
        return artifact_run(str(command), profile_key, str(run_id))
    return nullcontext()


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
        "match_only": options.get("match_only", False),
    }


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
