"""Main CLI command runner for Tawreed ordering workflows."""

from __future__ import annotations

import argparse
import concurrent.futures
import logging
from pathlib import Path

from src.core.artifact_run import artifact_run
from src.core.config.config_models import AppConfig, ProfileConfig
from src.core.drug_matching.ai.ai_rotation import configured_attempts
from src.core.drug_matching.config import APIConfig, load_env, resolve_api_config
from src.core.ordering.order_ai_matching import OrderAiSettings
from src.tawreed.tawreed import TawreedBot
from ..cli_shared import build_bot
from .cli_order_items import order_bot_options
from ..registry import register

logger = logging.getLogger(__name__)


# ============ AI Settings ============


def order_ai_settings(args: argparse.Namespace) -> OrderAiSettings:
    """Build live-order AI settings from CLI flags."""
    concurrency = max(1, int(getattr(args, "concurrency", None) or 5))
    return OrderAiSettings(
        enabled=bool(getattr(args, "ai", False)),
        api_config=order_api_config(args),
        concurrency=concurrency,
        accept_confidence=float(getattr(args, "ai_accept_confidence", 0.9)),
        verify_soft_accept_confidence=float(
            getattr(args, "ai_verify_soft_accept_confidence", 0.8)
        ),
        review_threshold=float(getattr(args, "ai_review_threshold", 0.95)),
        verify_policy=str(getattr(args, "ai_verify_policy", "score")),
        search_policy=str(getattr(args, "ai_search_policy", "review-candidates")),
    )


def order_api_config(args: argparse.Namespace) -> APIConfig:
    """Resolve AI API settings for live-order matching."""
    if getattr(args, "provider", None) == "rotation":
        return _rotation_api_config(args)
    resolved = resolve_api_config(
        getattr(args, "provider", None) or "",
        getattr(args, "model", None) or "",
        getattr(args, "api_key", None) or "",
    )
    return APIConfig(
        api_key=resolved["api_key"],
        api_keys=resolved.get("api_keys", ()),
        base_url=resolved["base_url"],
        model=resolved["model"],
        fallback_models=resolved.get("fallback_models", ()),
        review_model=getattr(args, "review_model", None) or "",
    )


def _rotation_api_config(args: argparse.Namespace) -> APIConfig:
    """Build API config for rotation-based provider selection."""
    attempts = configured_attempts("auto")
    first = attempts[0] if attempts else None
    return APIConfig(
        api_key=first.api_key if first else "",
        api_keys=(first.api_key,) if first else (),
        base_url=first.base_url if first else "",
        model=first.model if first else "",
        review_model=getattr(args, "review_model", None) or "",
        attempt_plan=attempts,
    )


# ============ Configuration ============


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
    from .cli_order_items import order_bot_options
    return build_bot(
        app_config,
        profile_key,
        profile,
        **order_bot_options(args),
    )


# ============ Main Command Runner ============


@register("order")
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
    from .cli_order_execution import run_single_profile

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
    from .cli_order_execution import run_single_profile

    logger.info(
        "running profiles in parallel",
        extra={"profile_count": len(profiles), "max_workers": max_workers},
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(run_single_profile, app_config, pk, p, args)
            for pk, p in profiles
        ]
        concurrent.futures.wait(futures)


__all__ = [
    # AI Settings
    "order_ai_settings",
    "order_api_config",
    # Configuration
    "apply_order_overrides",
    "resolve_max_workers",
    "order_bot",
    # Main Command
    "run_order_command",
    "execute_profiles",
    "run_parallel_profiles",
]
