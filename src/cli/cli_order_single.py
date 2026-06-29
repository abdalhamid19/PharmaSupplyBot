"""Single profile execution logic for Tawreed ordering."""

from __future__ import annotations

import argparse
from typing import Iterable

from ..core.artifact_run import artifact_run
from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.utils.excel import Item
from ..tawreed.tawreed import TawreedBot
from ..tawreed.tawreed_api_client import TawreedApiUnavailable
from ..tawreed.tawreed_session import SessionInvalidError
from .cli_shared import api_unavailable_exit, invalid_session_exit
from .cli_order_items_run import run_profile_items
from .cli_order_config import order_bot


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
    from .item_worker_pool import resolve_item_workers
    from .cli_order_parallel import run_parallel_order
    
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
