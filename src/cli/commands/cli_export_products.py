"""CLI command runner for Tawreed product catalog exports."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.core.artifact_run import artifact_run
from src.core.config.config_models import AppConfig
from src.tawreed.products.tawreed_product_export import (
    DEFAULT_EXPORT_PAGE_SIZE,
    export_tawreed_products,
)
from src.tawreed.auth.tawreed_session import SessionInvalidError
from ..cli_shared import build_bot, raise_invalid_session, require_state_file
from ..registry import register


@register("export-products")
def run_export_products_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Export Tawreed products for the selected authenticated profiles."""
    profiles = app_config.profiles_to_run(
        profile=args.profile, all_profiles=args.all_profiles
    )
    for profile_key, profile in profiles:
        with artifact_run("export-products", profile_key) as run:
            print(f"[{profile_key}] Artifact run: {run.directory}")
            _run_export_profile(app_config, profile_key, profile, args, run)
    return 0


def _run_export_profile(
    app_config: AppConfig, profile_key: str, profile, args: argparse.Namespace, run
) -> None:
    """Export one profile into its active run directory."""
    require_state_file(profile_key)
    bot = build_bot(app_config, profile_key, profile, args.debug_browser)
    try:
        export_tawreed_products(
            bot,
            run.directory,
            page_size=_positive_page_size(args.page_size),
            limit=max(int(args.limit), 0),
            stem=f"{args.stem}_{run.run_id}",
        )
    except SessionInvalidError as error:
        raise_invalid_session(profile_key, error)


def _positive_page_size(value: int) -> int:
    if int(value) <= 0:
        return DEFAULT_EXPORT_PAGE_SIZE
    return int(value)
