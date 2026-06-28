"""Main CLI command runner for Tawreed ordering workflows."""

from __future__ import annotations

import argparse
import concurrent.futures

from ..core.artifact_run import artifact_run
from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.drug_matching.config import load_env
from .cli_order_single import run_single_profile, run_single_profile_items
from .cli_order_config import apply_order_overrides, resolve_max_workers


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
