"""CLI command runner for Tawreed authentication workflows."""

from __future__ import annotations

import argparse

from src.core.config.config_models import AppConfig
from ..cli_shared import CommandTimer, build_bot, format_duration, is_quiet, print_command_summary
from ..registry import register


@register("auth")
def run_auth_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Authenticate and persist session state for the selected profiles."""
    timer = CommandTimer()
    with timer:
        profiles = app_config.profiles_to_run(
            profile=args.profile, all_profiles=args.all_profiles
        )
        authed: list[str] = []
        for profile_key, profile in profiles:
            bot = build_bot(app_config, profile_key, profile)
            is_headless = bool(getattr(args, "headless", False))
            auth_runner = bot.auth_headless if is_headless else bot.auth_interactive
            auth_runner(wait_seconds=int(args.wait_seconds))
            authed.append(profile_key)

    print_command_summary(
        "auth",
        {
            "profiles": authed,
            "headless": bool(getattr(args, "headless", False)),
            "duration": format_duration(timer.seconds),
        },
        success=True,
        quiet=is_quiet(args),
    )
    return 0
