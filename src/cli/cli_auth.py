"""CLI command runner for Tawreed authentication workflows."""

from __future__ import annotations

import argparse

from ..core.config.config_models import AppConfig
from .cli_shared import build_bot


def run_auth_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Authenticate and persist session state for the selected profiles."""
    profiles = app_config.profiles_to_run(profile=args.profile, all_profiles=args.all_profiles)
    for profile_key, profile in profiles:
        bot = build_bot(app_config, profile_key, profile)
        is_headless = bool(getattr(args, "headless", False))
        auth_runner = bot.auth_headless if is_headless else bot.auth_interactive
        auth_runner(wait_seconds=int(args.wait_seconds))
    return 0
