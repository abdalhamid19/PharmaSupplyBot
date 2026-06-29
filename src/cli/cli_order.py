"""Main CLI command runner for Tawreed ordering workflows."""

from __future__ import annotations

import argparse
import concurrent.futures
import multiprocessing
from pathlib import Path
from typing import Any, Iterable

from ..core.artifact_run import artifact_run, current_artifact_run
from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.drug_matching.ai_rotation import configured_attempts
from ..core.drug_matching.config import APIConfig, load_env, resolve_api_config
from ..core.order_ai_matching import OrderAiSettings
from ..core.utils.chunking import split_into_chunks
from ..core.utils.excel import Item
from ..tawreed.order_result_merger import merge_worker_summaries
from ..tawreed.order_worker_artifact_merger import merge_order_worker_artifacts
from ..tawreed.tawreed import TawreedBot
from ..tawreed.tawreed_api_client import TawreedApiUnavailable
from ..tawreed.tawreed_session import SessionInvalidError
from .cli_shared import api_unavailable_exit, build_bot, invalid_session_exit
from .cli_order_items import summary_label, match_only
from .item_worker import report_worker_results


# ============ AI Settings ============


def order_ai_settings(args: argparse.Namespace) -> OrderAiSettings:
    """Build live-order AI settings from CLI flags."""
    concurrency = max(1, int(getattr(args, "concurrency", None) or 5))
    return OrderAiSettings(
        enabled=bool(getattr(args, "ai", False)),
        api_config=order_api_config(args),
        concurrency=concurrency,
        accept_confidence=float(getattr(args, "ai_accept_confidence", 0.9)),
        verify_soft_accept_confidence=float(
            getattr(args, "ai_verify_soft_accept_confidence", 0.8)
        ),
        review_threshold=float(getattr(args, "ai_review_threshold", 0.95)),
        verify_policy=str(getattr(args, "ai_verify_policy", "score")),
        search_policy=str(getattr(args, "ai_search_policy", "review-candidates")),
    )


def order_api_config(args: argparse.Namespace) -> APIConfig:
    """Resolve AI API settings for live-order matching."""
    if getattr(args, "provider", None) == "rotation":
        return _rotation_api_config(args)
    resolved = resolve_api_config(
        getattr(args, "provider", None) or "",
        getattr(args, "model", None) or "",
        getattr(args, "api_key", None) or "",
    )
    return APIConfig(
        api_key=resolved["api_key"],
        api_keys=resolved.get("api_keys", ()),
        base_url=resolved["base_url"],
        model=resolved["model"],
        fallback_models=resolved.get("fallback_models", ()),
        review_model=getattr(args, "review_model", None) or "",
    )


def _rotation_api_config(args: argparse.Namespace) -> APIConfig:
    """Build API config for rotation-based provider selection."""
    attempts = configured_attempts("auto")
    first = attempts[0] if attempts else None
    return APIConfig(
        api_key=first.api_key if first else "",
        api_keys=(first.api_key,) if first else (),
        base_url=first.base_url if first else "",
        model=first.model if first else "",
        review_model=getattr(args, "review_model", None) or "",
        attempt_plan=attempts,
    )


# ============ Configuration ============


def apply_order_overrides(app_config: AppConfig, args: argparse.Namespace) -> None:
    """Apply optional per-run order settings to the loaded application config."""
    warehouse_mode = getattr(args, "warehouse_mode", None)
    if warehouse_mode:
        app_config.warehouse_strategy["mode"] = str(warehouse_mode)
    min_discount_percent = getattr(args, "min_discount_percent", None)
    if min_discount_percent is not None:
        app_config.warehouse_strategy["min_discount_percent"] = float(
            min_discount_percent
        )


def resolve_max_workers(
    app_config: AppConfig, args: argparse.Namespace, profile_count: int
) -> int:
    """Return the final concurrency limit for this run."""
    limit = getattr(args, "max_workers", None)
    if limit is None:
        limit = app_config.runtime.max_workers
    if limit <= 0:
        return profile_count
    return min(limit, profile_count)


def order_bot(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    args: argparse.Namespace,
) -> TawreedBot:
    """Build the bot used for one profile order run."""
    from .cli_order_items import order_bot_options
    return build_bot(
        app_config,
        profile_key,
        profile,
        **order_bot_options(args),
    )


# ============ Main Command Runner ============


def run_order_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Place orders from Excel for the selected profiles."""
    load_env()
    apply_order_overrides(app_config, args)
    profiles = app_config.profiles_to_run(
        profile=args.profile, all_profiles=args.all_profiles
    )
    execute_profiles(app_config, profiles, args)
    return 0


def execute_profiles(
    app_config: AppConfig,
    profiles: list[tuple[str, ProfileConfig]],
    args: argparse.Namespace,
) -> None:
    """Run the selected profiles either sequentially or in parallel."""
    max_workers = resolve_max_workers(app_config, args, len(profiles))
    if max_workers <= 1:
        for profile_key, profile in profiles:
            run_single_profile(app_config, profile_key, profile, args)
        return

    run_parallel_profiles(app_config, profiles, args, max_workers)


def run_parallel_profiles(
    app_config: AppConfig,
    profiles: list[tuple[str, ProfileConfig]],
    args: argparse.Namespace,
    max_workers: int,
) -> None:
    """Submit profile-level order runs to the configured thread pool."""
    print(
        f"Running {len(profiles)} profiles in parallel (max_workers={max_workers})..."
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(run_single_profile, app_config, pk, p, args)
            for pk, p in profiles
        ]
        concurrent.futures.wait(futures)


# ============ Single Profile Execution ============


def run_single_profile(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    args: argparse.Namespace,
) -> None:
    """Prepare and run a single profile order flow."""
    with artifact_run("order", profile_key) as run:
        print(f"[{profile_key}] Artifact run: {run.directory}")
        run_single_profile_items(app_config, profile_key, profile, args)


def run_single_profile_items(
    app_config: AppConfig, profile_key: str, profile: ProfileConfig, args: argparse.Namespace
) -> None:
    """Run a profile once its artifact context is active."""
    from .cli_order_items import (
        load_order_items,
        prepared_order_items,
        limited_order_items,
        ensure_non_empty_items,
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
    from .item_worker import run_order_chunk

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
    from .item_worker import run_order_chunk
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
    # AI Settings
    "order_ai_settings",
    "order_api_config",
    # Configuration
    "apply_order_overrides",
    "resolve_max_workers",
    "order_bot",
    # Main Command
    "run_order_command",
    "execute_profiles",
    "run_parallel_profiles",
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
