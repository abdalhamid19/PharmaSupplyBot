"""Configuration logic for Tawreed ordering."""

from __future__ import annotations

import argparse

from ..core.config.config_models import AppConfig, ProfileConfig
from ..tawreed.tawreed import TawreedBot
from .cli_shared import build_bot
from .cli_order_items import order_bot_options


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
