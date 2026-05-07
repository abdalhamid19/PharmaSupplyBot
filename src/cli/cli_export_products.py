"""CLI command runner for Tawreed product catalog exports."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..core.config.config_models import AppConfig
from ..tawreed.tawreed_product_export_api import DEFAULT_EXPORT_PAGE_SIZE
from ..tawreed.tawreed_product_export_flow import export_tawreed_products
from ..tawreed.tawreed_session import SessionInvalidError
from .cli_shared import build_bot, invalid_session_exit, require_state_file


def run_export_products_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Export Tawreed products for the selected authenticated profiles."""
    profiles = app_config.profiles_to_run(
        profile=args.profile, all_profiles=args.all_profiles
    )
    for profile_key, profile in profiles:
        require_state_file(profile_key)
        bot = build_bot(app_config, profile_key, profile, args.debug_browser)
        try:
            export_tawreed_products(
                bot,
                _profile_output_dir(args.output_dir, profile_key),
                page_size=_positive_page_size(args.page_size),
                limit=max(int(args.limit), 0),
                stem=str(args.stem),
            )
        except SessionInvalidError as error:
            raise invalid_session_exit(app_config.base_url, profile_key, error)
    return 0


def _profile_output_dir(template: str, profile_key: str) -> Path:
    return Path(template.format(profile=profile_key))


def _positive_page_size(value: int) -> int:
    if int(value) <= 0:
        return DEFAULT_EXPORT_PAGE_SIZE
    return int(value)
