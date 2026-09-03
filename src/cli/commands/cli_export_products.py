"""CLI command runner for Tawreed product catalog exports."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.core.artifact_run import artifact_run
from src.core.config.config_models import AppConfig
from src.tawreed.products.tawreed_product_export import (
    DEFAULT_EXPORT_PAGE_SIZE,
    export_tawreed_products,
)
from src.tawreed.auth.tawreed_session import SessionInvalidError
from ..cli_shared import (
    CommandTimer,
    build_bot,
    format_duration,
    is_quiet,
    print_command_summary,
    raise_invalid_session,
    require_state_file,
)
from ..registry import register

logger = logging.getLogger(__name__)


@register("export-products")
def run_export_products_command(
    app_config: AppConfig, args: argparse.Namespace
) -> int:
    """Export Tawreed products for the selected authenticated profiles."""
    timer = CommandTimer()
    output_paths: list[Path] = []
    with timer:
        profiles = app_config.profiles_to_run(
            profile=args.profile, all_profiles=args.all_profiles
        )
        for profile_key, profile in profiles:
            with artifact_run("export-products", profile_key) as run:
                logger.info(
                    "artifact run started",
                    extra={"profile": profile_key, "directory": str(run.directory)},
                )
                _run_export_profile(app_config, profile_key, profile, args, run)
                output_paths.append(run.directory)

    print_command_summary(
        "export-products",
        {
            "profiles": [p for p, _ in profiles],
            "artifacts": output_paths,
            "duration": format_duration(timer.seconds),
        },
        success=True,
        quiet=is_quiet(args),
    )
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
