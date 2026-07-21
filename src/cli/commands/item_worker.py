"""Item-level worker subprocess and pool utilities."""

from __future__ import annotations
import logging

from contextlib import nullcontext
from pathlib import Path
from typing import Any

from src.core.artifact_run import artifact_run, current_artifact_run
from src.core.config.config import load_config
from src.core.utils.excel import Item
from src.tawreed.auth.tawreed_session import SessionInvalidError
from ..cli_shared import build_bot, raise_invalid_session

logger = logging.getLogger(__name__)


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


def resolve_item_workers(app_config: object, args: object) -> int:
    """Return the effective item-level worker count for one command run."""
    cli_value = getattr(args, "item_workers", None)
    if cli_value is not None:
        return int(cli_value)
    runtime = getattr(app_config, "runtime", None)
    return int(getattr(runtime, "item_workers", 1))


def build_cart_payloads(
    profile_key: str,
    chunks: list[list[Any]],
    args: object,
    auth_lock=None,
) -> list[dict[str, Any]]:
    """Build serializable payloads for cart-removal item workers."""
    return [
        _cart_payload(profile_key, chunk, index, args, auth_lock)
        for index, chunk in enumerate(chunks)
    ]


def _cart_payload(
    profile_key: str, chunk: list[Any], index: int, args: object, auth_lock=None
) -> dict[str, Any]:
    """Build one serializable cart-removal worker payload."""
    return {
        "config_path": str(Path(getattr(args, "config", "state/config.yaml"))),
        "profile_key": profile_key,
        "items": [(item.code, item.name) for item in chunk],
        "worker_id": index,
        "options": _cart_options(args, auth_lock),
    }


def _cart_options(args: object, auth_lock=None) -> dict[str, Any]:
    """Return serializable cart-removal worker options."""
    run = current_artifact_run()
    return {
        "artifact_command": run.command if run else "",
        "artifact_run_id": run.run_id if run else "",
        "debug_browser": bool(getattr(args, "debug_browser", False)),
        "stop_flag": getattr(args, "stop_flag", None),
        "execution_mode": str(getattr(args, "execution_mode", "auto")),
        "auth_lock": auth_lock,
    }


def report_worker_results(
    base_url: str,
    profile_key: str,
    results: list[dict[str, Any]],
) -> None:
    """Log worker outcomes and raise the standard invalid-session exit."""
    for result in results:
        status = result.get("status")
        if status == "session_invalid":
            error = SessionInvalidError(str(result.get("error", "")))
            raise_invalid_session(profile_key, error)
        if status == "error":
            logger.warning("worker error", extra={"profile": profile_key, "error": result.get("error", "")})


def run_order_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    """Process one chunk of order items in an isolated subprocess."""
    profile_key, bot = _build_worker_bot(payload)
    items = [Item(code=r[0], name=r[1], qty=r[2]) for r in payload["items"]]
    with _worker_artifact_run(payload, profile_key):
        return execute_order_worker(bot, items, profile_key)


def run_cart_removal_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    """Process one chunk of cart-removal items in an isolated subprocess."""
    from src.core.cart.cart_removal_items import CartRemovalItem

    profile_key, bot = _build_worker_bot(payload)
    items = [CartRemovalItem(code=r[0], name=r[1]) for r in payload["items"]]
    with _worker_artifact_run(payload, profile_key):
        return execute_cart_removal_worker(bot, items, profile_key)


def _worker_artifact_run(payload: dict[str, Any], profile_key: str):
    """Return a run context for subprocess artifact writes."""
    options = payload.get("options", {})
    command = options.get("artifact_command")
    run_id = options.get("artifact_run_id")
    if command and run_id:
        return artifact_run(str(command), profile_key, str(run_id))
    return nullcontext()


def _build_worker_bot(payload: dict[str, Any]):
    """Reconstruct config, profile, and bot from the serialized payload."""
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
        "order_ai_settings": options.get("order_ai_settings"),
        "execution_mode": options.get("execution_mode", "auto"),
        "matching_risk_policy": options.get("matching_risk_policy", "safe"),
        "flagged_match_action": options.get("flagged_match_action", "manual-review-only"),
        "auth_lock": options.get("auth_lock"),
        "worker_id": worker_id,
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


__all__ = [
    "execute_order_worker",
    "execute_cart_removal_worker",
    "resolve_item_workers",
    "build_cart_payloads",
    "report_worker_results",
    "run_order_chunk",
    "run_cart_removal_chunk",
]
