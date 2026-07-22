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
    from ..cli_shared import (
        CommandTimer,
        format_duration,
        is_quiet,
        print_command_summary,
    )

    load_env()
    apply_order_overrides(app_config, args)
    profiles = app_config.profiles_to_run(
        profile=args.profile, all_profiles=args.all_profiles
    )

    timer = CommandTimer()
    run_directories: list[Path] = []
    processed = matched = flagged = 0
    with timer:
        from src.core.artifact_run import current_artifact_run

        execute_profiles(app_config, profiles, args)

        # Snapshot: pull active run (if still set) + fall back to the
        # most recent run directory per profile from disk.
        active = current_artifact_run()
        if active and active.directory.exists():
            run_directories.append(active.directory)
        else:
            for profile_key, _ in profiles:
                run_directories.extend(_newest_run_dirs(profile_key))

        # Read counters from CSVs in THIS run's directory only.
        # We only count ``order_item_summary_*.csv`` — that file has
        # one row per INPUT item, which is what the operator means
        # by "processed". The ``match_only_summary_*.csv`` file has
        # one row per CANDIDATE (many candidates per item when AI
        # runs), so we deliberately exclude it to avoid inflating
        # the counter.
        for d in run_directories:
            for path in d.glob("order_item_summary_*.csv"):
                p, m, f = _count_from_summary_csvs([path])
                processed += p
                matched += m
                flagged += f

    # The "summary" field shows the first run's directory (or the
    # active one if available) so the operator can `ls` / open the
    # artifacts without guessing.
    primary_dir = run_directories[0] if run_directories else None

    print_command_summary(
        "order",
        {
            "processed": processed,
            "matched": matched,
            "flagged": flagged,
            "duration": format_duration(timer.seconds),
            "summary": primary_dir,
        },
        success=True,
        quiet=is_quiet(args),
    )
    return 0


def _newest_run_dirs(profile_key: str) -> list[Path]:
    """Return the most recent run directories under
    ``artifacts/order/<profile>/**/`` (one per timestamp).
    """
    base = Path("artifacts") / "order" / profile_key
    if not base.exists():
        base = Path("artifacts") / profile_key
    if not base.exists():
        return []
    dirs = [d for d in base.iterdir() if d.is_dir()]
    # Sort by directory name (which is the timestamped run_id) — newest last.
    dirs.sort(key=lambda d: d.name, reverse=True)
    return [dirs[0]] if dirs else []


def _count_from_summary_csvs(paths: list[Path]) -> tuple[int, int, int]:
    """Return ``(processed, matched, flagged)`` totals across CSVs.

    Reads each CSV's ``status`` and ``manual_review_required`` columns
    if present. Returns ``(0, 0, 0)`` when no CSVs are readable so
    the caller still gets a clean summary block.

    Status values we recognise (from src/tawreed/order/tawreed_order_summary.py):
      * "matched-only"   — we found a candidate, did not add to cart
      * "added-to-cart"  — successful end-to-end placement
      * "no-results"     — no candidate matched the query
      * "not-orderable"  — candidate found but can't be ordered
      * "failed"         — errored mid-flow
      * "manual-review"  — requires human review (counted as flagged)

    The ``matched`` total includes both ``matched-only`` and
    ``added-to-cart`` since both indicate a successful match
    (whether or not it was placed). The ``flagged`` total is rows
    whose ``manual_review_required`` column is truthy.
    """
    if not paths:
        return 0, 0, 0
    total = matched = flagged = 0
    try:
        import csv as _csv

        for path in paths:
            with path.open("r", encoding="utf-8", newline="") as fh:
                reader = _csv.DictReader(fh)
                for row in reader:
                    total += 1
                    status = str(row.get("status", "")).strip()
                    if status in ("matched-only", "added-to-cart"):
                        matched += 1
                    mr = str(row.get("manual_review_required", "")).strip().lower()
                    if mr in ("true", "1", "yes"):
                        flagged += 1
    except (OSError, KeyError, ValueError):
        return 0, 0, 0
    return total, matched, flagged


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
