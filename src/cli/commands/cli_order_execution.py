"""Order execution logic for single and parallel profile runs."""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from typing import Any, Iterable

from src.core.artifact_run import current_artifact_run
from src.core.utils.chunking import split_into_chunks
from src.core.utils.excel import Item
from src.tawreed.artifacts.order_result_merger import merge_worker_summaries
from src.tawreed.artifacts.order_worker_artifact_merger import merge_order_worker_artifacts
from src.tawreed.tawreed import TawreedBot
from src.tawreed.api.tawreed_api_client import TawreedApiUnavailable
from src.tawreed.auth.tawreed_session import SessionInvalidError
from .cli_order import order_ai_settings, order_bot
from .cli_order_items import match_only, summary_label
from ..cli_shared import api_unavailable_exit, invalid_session_exit
from .item_worker import report_worker_results, run_order_chunk


# ============ Single Profile Execution ============


def run_single_profile(
    app_config,
    profile_key: str,
    profile,
    args,
) -> None:
    """Prepare and run a single profile order flow."""
    from src.core.artifact_run import artifact_run

    with artifact_run("order", profile_key) as run:
        print(f"[{profile_key}] Artifact run: {run.directory}")
        run_single_profile_items(app_config, profile_key, profile, args)


def run_single_profile_items(
    app_config, profile_key: str, profile, args
) -> None:
    """Run a profile once its artifact context is active."""
    from .cli_order_items import (
        ensure_non_empty_items,
        limited_order_items,
        load_order_items,
        prepared_order_items,
    )
    from .item_worker import resolve_item_workers

    items = load_order_items(app_config, args)
    profile_items = prepared_order_items(profile_key, items, args)
    profile_items = limited_order_items(profile_items, args)
    profile_items = ensure_non_empty_items(profile_key, profile_items)
    if profile_items is None:
        return
    item_workers = resolve_item_workers(app_config, args)
    if item_workers > 1:
        run_parallel_order(app_config, profile_key, profile_items, args, item_workers)
        return
    bot = order_bot(app_config, profile_key, profile, args)
    run_profile_items(app_config.base_url, profile_key, bot, profile_items, args)


def run_profile_items(
    base_url: str, profile_key: str, bot: TawreedBot, items: Iterable[Item], args
) -> None:
    """Run one profile through the requested order mode."""
    if match_only(args):
        run_profile_match_only(base_url, profile_key, bot, items)
        return
    run_profile_order(base_url, profile_key, bot, items)


def run_profile_order(
    base_url: str, profile_key: str, bot: TawreedBot, items: Iterable[Item]
) -> None:
    """Run one profile order flow and handle session-expiry failures uniformly."""
    try:
        bot.place_order_from_items(items)
    except TawreedApiUnavailable as error:
        raise api_unavailable_exit(profile_key, error) from error
    except SessionInvalidError as error:
        raise invalid_session_exit(base_url, profile_key, error) from error


def run_profile_match_only(
    base_url: str, profile_key: str, bot: TawreedBot, items: Iterable[Item]
) -> None:
    """Run product matching only and handle session-expiry failures uniformly."""
    try:
        bot.match_items_only(items)
    except TawreedApiUnavailable as error:
        raise api_unavailable_exit(profile_key, error) from error
    except SessionInvalidError as error:
        raise invalid_session_exit(base_url, profile_key, error) from error


# ============ Parallel Order Execution ============


def run_parallel_order(
    app_config,
    profile_key: str,
    items,
    args,
    item_workers: int,
) -> None:
    """Split items across multiprocessing workers and merge results."""
    from multiprocessing import Manager

    materialized = list(items)
    chunks = split_into_chunks(materialized, item_workers)
    manager = Manager()
    auth_lock = manager.Lock()

    payloads = build_order_payloads(profile_key, chunks, args, auth_lock)
    results = execute_order_workers(profile_key, chunks, payloads)
    merge_order_worker_outputs(profile_key, args)
    report_worker_results(app_config.base_url, profile_key, results)


def execute_order_workers(profile_key, chunks, payloads):
    """Execute order workers in parallel."""
    print(f"[{profile_key}] Launching {len(chunks)} parallel item workers...")
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(processes=len(chunks)) as pool:
        return pool.map(run_order_chunk, payloads)


def merge_order_worker_outputs(profile_key: str, args) -> None:
    """Merge all order worker output partitions for the active run."""
    merge_worker_summaries(profile_key, summary_label(args))
    merge_order_worker_artifacts(
        profile_key, ("order_item_summary", "order_ai_trace", "manual_review")
    )


def build_order_payloads(
    profile_key: str,
    chunks: list[list[Any]],
    args,
    auth_lock,
) -> list[dict[str, Any]]:
    """Build serializable payloads for each order worker."""
    config_path = str(Path(getattr(args, "config", "config.yaml")))
    options = worker_options(args, auth_lock)
    return [
        {
            "config_path": config_path,
            "profile_key": profile_key,
            "items": [(it.code, it.name, it.qty) for it in chunk],
            "worker_id": idx,
            "options": options,
        }
        for idx, chunk in enumerate(chunks)
    ]


def worker_options(args, auth_lock=None) -> dict[str, Any]:
    """Extract serializable worker options from the CLI namespace."""
    run = current_artifact_run()
    return {
        "artifact_command": run.command if run else "",
        "artifact_run_id": run.run_id if run else "",
        "order_ai_settings": order_ai_settings(args),
        "debug_browser": bool(getattr(args, "debug_browser", False)),
        "fast_search": bool(getattr(args, "fast_search", False)),
        "match_only": match_only(args),
        "execution_mode": str(getattr(args, "execution_mode", "auto")),
        "matching_risk_policy": str(getattr(args, "matching_risk_policy", "safe")),
        "flagged_match_action": str(
            getattr(args, "flagged_match_action", "manual-review-only")
        ),
        "stop_flag": getattr(args, "stop_flag", None),
        "warehouse_mode": getattr(args, "warehouse_mode", None),
        "min_discount_percent": getattr(args, "min_discount_percent", None),
        "auth_lock": auth_lock,
    }


__all__ = [
    # Single Profile
    "run_single_profile",
    "run_single_profile_items",
    "run_profile_items",
    "run_profile_order",
    "run_profile_match_only",
    # Parallel Order
    "run_parallel_order",
    "execute_order_workers",
    "merge_order_worker_outputs",
    "build_order_payloads",
    "worker_options",
]
