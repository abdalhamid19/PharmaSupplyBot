"""CLI command runner for Tawreed cart-removal workflows."""

from __future__ import annotations

import argparse
import multiprocessing
from pathlib import Path
from typing import Any

from ..core.artifact_run import artifact_run
from ..core.cart_removal_items import load_cart_removal_items
from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.utils.chunking import split_into_chunks
from ..tawreed.order_result_merger import merge_worker_summaries
from ..tawreed.tawreed import TawreedBot
from ..tawreed.tawreed_session import SessionInvalidError
from .cli_shared import build_bot, invalid_session_exit, require_state_file
from .cli_cart_removal_source import cart_removal_items
from .item_worker_pool import (
    build_cart_payloads,
    report_worker_results,
    resolve_item_workers,
)


def run_remove_cart_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Remove requested items from Tawreed carts for the selected profiles."""
    profiles = app_config.profiles_to_run(
        profile=args.profile, all_profiles=args.all_profiles
    )
    for profile_key, profile in profiles:
        with artifact_run("remove-cart", profile_key) as run:
            print(f"[{profile_key}] Artifact run: {run.directory}")
            _run_remove_cart_profile(app_config, profile_key, profile, args)
    return 0


def _run_remove_cart_profile(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    args: argparse.Namespace,
) -> None:
    """Run one cart-removal profile with the active artifact context."""
    require_state_file(profile_key)
    items = cart_removal_items(args, load_cart_removal_items)
    item_workers = resolve_item_workers(app_config, args)
    if item_workers > 1 and len(items) > 1:
        _run_parallel_cart_removal(app_config, profile_key, items, args, item_workers)
        return
    bot = _remove_cart_bot(app_config, profile_key, profile, args)
    _run_profile_cart_removal(app_config.base_url, profile_key, bot, iter(items))


def _remove_cart_bot(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    args: argparse.Namespace,
) -> TawreedBot:
    """Build the bot used for one profile cart-removal run."""
    stop_flag = getattr(args, "stop_flag", None)
    return build_bot(
        app_config,
        profile_key,
        profile,
        debug_browser=bool(getattr(args, "debug_browser", False)),
        stop_flag_path=Path(stop_flag) if stop_flag else None,
        execution_mode=str(getattr(args, "execution_mode", "auto")),
    )


def _run_profile_cart_removal(
    base_url: str, profile_key: str, bot: TawreedBot, items: Any
) -> None:
    """Run one profile cart-removal flow and handle session-expiry failures."""
    try:
        bot.remove_cart_items(items)
    except SessionInvalidError as error:
        raise invalid_session_exit(base_url, profile_key, error) from error


def _run_parallel_cart_removal(
    app_config: AppConfig,
    profile_key: str,
    items: list,
    args: argparse.Namespace,
    item_workers: int,
) -> None:
    """Split cart-removal items across multiprocessing workers and merge."""
    from multiprocessing import Manager
    from .item_worker_runner import run_cart_removal_chunk

    chunks = split_into_chunks(items, item_workers)
    manager = Manager()
    auth_lock = manager.Lock()
    
    payloads = build_cart_payloads(profile_key, chunks, args, auth_lock)
    results = _execute_cart_workers(profile_key, chunks, payloads)
    merge_worker_summaries(profile_key, "cart_removal_summary")
    report_worker_results(app_config.base_url, profile_key, results)


def _execute_cart_workers(profile_key, chunks, payloads):
    """Execute cart removal workers in parallel."""
    from .item_worker_runner import run_cart_removal_chunk
    print(f"[{profile_key}] Launching {len(chunks)} parallel cart-removal workers...")
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(processes=len(chunks)) as pool:
        return pool.map(run_cart_removal_chunk, payloads)
