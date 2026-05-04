"""CLI command runner for Tawreed cart-removal workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..core.cart_removal_items import load_cart_removal_items
from ..core.config.config_models import AppConfig, ProfileConfig
from ..tawreed.tawreed import TawreedBot
from ..tawreed.tawreed_session import SessionInvalidError
from .cli_shared import build_bot, invalid_session_exit, require_state_file


def run_remove_cart_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Remove requested items from Tawreed carts for the selected profiles."""
    items = load_cart_removal_items(Path(args.excel))
    if not items:
        print("No items found from cart-removal Excel.")
        return 0

    profiles = app_config.profiles_to_run(profile=args.profile, all_profiles=args.all_profiles)
    for profile_key, profile in profiles:
        require_state_file(profile_key)
        bot = _remove_cart_bot(app_config, profile_key, profile, args)
        _run_profile_cart_removal(app_config.base_url, profile_key, bot, items)
    return 0


def _remove_cart_bot(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    args: argparse.Namespace,
) -> TawreedBot:
    """Build the bot used for one profile cart-removal run."""
    return build_bot(
        app_config,
        profile_key,
        profile,
        debug_browser=bool(getattr(args, "debug_browser", False)),
    )


def _run_profile_cart_removal(
    base_url: str,
    profile_key: str,
    bot: TawreedBot,
    items: list,
) -> None:
    """Run one profile cart-removal flow and handle session-expiry failures uniformly."""
    try:
        bot.remove_cart_items(items)
    except SessionInvalidError as error:
        raise invalid_session_exit(base_url, profile_key, error) from error
