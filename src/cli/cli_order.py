"""CLI command runner for Tawreed ordering workflows."""

from __future__ import annotations

import argparse
import concurrent.futures
from pathlib import Path
from typing import Iterable

from ..core.artifact_run import artifact_run
from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.drug_matching.config import load_env
from ..core.utils.excel import Item
from ..tawreed.tawreed import TawreedBot
from ..tawreed.tawreed_api import TawreedApiUnavailable
from ..tawreed.tawreed_session import SessionInvalidError
from .cli_shared import (
    api_unavailable_exit,
    build_bot,
    invalid_session_exit,
)
from .cli_order_ai import order_ai_settings
from .cli_order_items import (
    ensure_non_empty_items,
    limited_order_items,
    load_order_items,
    match_only,
    order_bot_options,
    prepared_order_items,
)
from .cli_order_parallel import run_parallel_order
from .item_worker_pool import resolve_item_workers


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
    run_profile_items(app_config, profile_key, bot, profile_items, args)


def run_profile_items(
    app_config: AppConfig,
    profile_key: str,
    bot: TawreedBot,
    items: Iterable[Item],
    args: argparse.Namespace,
) -> None:
    """Run one profile through the requested order mode."""
    if match_only(args):
        run_profile_match_only(app_config.base_url, profile_key, bot, items)
        return
    run_profile_order(app_config.base_url, profile_key, bot, items)


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


def order_bot(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    args: argparse.Namespace,
) -> TawreedBot:
    """Build the bot used for one profile order run."""
    return build_bot(
        app_config,
        profile_key,
        profile,
        **order_bot_options(args),
    )


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
