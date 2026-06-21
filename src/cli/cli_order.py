"""CLI command runner for Tawreed ordering workflows."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import itertools
import multiprocessing
from pathlib import Path
from typing import Any, Iterable

from ..core.artifact_run import artifact_run, current_artifact_run
from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.drug_matching.config import load_env
from ..core.manual_review_corrections import corrected_items_from_manual_review_csv
from ..core.prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    filter_prevented_order_items,
    is_prevented_items_excel_path,
    load_prevented_items,
)
from ..core.utils.chunking import split_into_chunks
from ..core.utils.excel import (
    Item,
    load_items_from_excel,
    load_match_only_items_from_excel,
)
from ..tawreed.order_result_merger import merge_worker_summaries
from ..tawreed.order_worker_artifact_merger import merge_order_worker_artifacts
from ..tawreed.tawreed import TawreedBot
from ..tawreed.tawreed_api import TawreedApiUnavailable
from ..tawreed.tawreed_match_only_summary import MATCH_ONLY_SUMMARY_LABEL
from ..tawreed.tawreed_session import SessionInvalidError
from .cli_shared import (
    api_unavailable_exit,
    build_bot,
    invalid_session_exit,
    require_state_file,
)
from .cli_order_ai import order_ai_settings
from .item_worker_pool import report_worker_results, resolve_item_workers


def run_order_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Place orders from Excel for the selected profiles."""
    load_env()
    _apply_order_overrides(app_config, args)
    profiles = app_config.profiles_to_run(
        profile=args.profile, all_profiles=args.all_profiles
    )
    _execute_profiles(app_config, profiles, args)
    return 0


def _execute_profiles(
    app_config: AppConfig,
    profiles: list[tuple[str, ProfileConfig]],
    args: argparse.Namespace,
) -> None:
    """Run the selected profiles either sequentially or in parallel."""
    max_workers = _resolve_max_workers(app_config, args, len(profiles))
    if max_workers <= 1:
        for profile_key, profile in profiles:
            _run_single_profile(app_config, profile_key, profile, args)
        return

    _run_parallel_profiles(app_config, profiles, args, max_workers)


def _run_parallel_profiles(
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
            executor.submit(_run_single_profile, app_config, pk, p, args)
            for pk, p in profiles
        ]
        concurrent.futures.wait(futures)


def _resolve_max_workers(
    app_config: AppConfig, args: argparse.Namespace, profile_count: int
) -> int:
    """Return the final concurrency limit for this run."""
    limit = getattr(args, "max_workers", None)
    if limit is None:
        limit = app_config.runtime.max_workers
    if limit <= 0:
        return profile_count
    return min(limit, profile_count)


def _run_single_profile(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    args: argparse.Namespace,
) -> None:
    """Prepare and run a single profile order flow."""
    with artifact_run("order", profile_key) as run:
        print(f"[{profile_key}] Artifact run: {run.directory}")
        _run_single_profile_items(app_config, profile_key, profile, args)


def _run_single_profile_items(
    app_config: AppConfig, profile_key: str, profile: ProfileConfig, args: argparse.Namespace
) -> None:
    """Run a profile once its artifact context is active."""
    items = _load_order_items(app_config, args)
    profile_items = _prepared_order_items(profile_key, items, args)
    profile_items = _limited_order_items(profile_items, args)
    profile_items = _ensure_non_empty_items(profile_key, profile_items)
    if profile_items is None:
        return
    item_workers = resolve_item_workers(app_config, args)
    if item_workers > 1:
        _run_parallel_order(app_config, profile_key, profile_items, args, item_workers)
        return
    bot = _order_bot(app_config, profile_key, profile, args)
    _run_profile_items(app_config, profile_key, bot, profile_items, args)


def _run_profile_items(
    app_config: AppConfig,
    profile_key: str,
    bot: TawreedBot,
    items: Iterable[Item],
    args: argparse.Namespace,
) -> None:
    """Run one profile through the requested order mode."""
    if _match_only(args):
        _run_profile_match_only(app_config.base_url, profile_key, bot, items)
        return
    _run_profile_order(app_config.base_url, profile_key, bot, items)


def _ensure_non_empty_items(
    profile_key: str,
    items: Iterable[Item],
) -> Iterable[Item] | None:
    """Return an iterable that is guaranteed to yield at least one item, else None."""
    _, probe_iter = itertools.tee(items)
    try:
        first_item = next(probe_iter)
    except StopIteration:
        print(f"[{profile_key}] No remaining items to process.")
        return None
    return itertools.chain([first_item], probe_iter)


def _apply_order_overrides(app_config: AppConfig, args: argparse.Namespace) -> None:
    """Apply optional per-run order settings to the loaded application config."""
    warehouse_mode = getattr(args, "warehouse_mode", None)
    if warehouse_mode:
        app_config.warehouse_strategy["mode"] = str(warehouse_mode)
    min_discount_percent = getattr(args, "min_discount_percent", None)
    if min_discount_percent is not None:
        app_config.warehouse_strategy["min_discount_percent"] = float(
            min_discount_percent
        )


def _load_order_items(
    app_config: AppConfig, args: argparse.Namespace
) -> Iterable[Item]:
    """Load and filter order items iteratively."""
    correction_items = _manual_review_correction_items(args)
    if correction_items is not None:
        return correction_items
    _require_order_excel(args)
    return _load_regular_order_items(app_config, args)


def _load_regular_order_items(
    app_config: AppConfig, args: argparse.Namespace
) -> Iterable[Item]:
    """Load regular order items from the configured Excel source."""
    excel_path = Path(args.excel)
    prevented_path = _prevented_items_path(args)
    _reject_prevented_excel_as_order_source(excel_path, prevented_path)
    has_prevented_filter = bool(prevented_path and prevented_path.is_file())
    items = _load_items_for_order_mode(
        excel_path,
        app_config,
        args,
        has_prevented_filter,
    )
    if has_prevented_filter and prevented_path is not None:
        prevented_items = load_prevented_items(prevented_path)
        items = filter_prevented_order_items(items, prevented_items)
    return items


def _manual_review_correction_items(args: argparse.Namespace) -> Iterable[Item] | None:
    corrections = getattr(args, "from_manual_review_corrections", None)
    if not corrections:
        return None
    args.match_only = True
    return corrected_items_from_manual_review_csv(Path(corrections))


def _require_order_excel(args: argparse.Namespace) -> None:
    if not getattr(args, "excel", None):
        raise SystemExit("Provide --excel or --from-manual-review-corrections.")


def _load_items_for_order_mode(
    excel_path: Path,
    app_config: AppConfig,
    args: argparse.Namespace,
    has_prevented_filter: bool,
) -> Iterable[Item]:
    """Load items with a two-column catalog fallback in match-only mode."""
    limit = _excel_load_limit(args, has_prevented_filter)
    if _match_only(args):
        return load_match_only_items_from_excel(
            excel_path, app_config.excel, limit=limit
        )
    return load_items_from_excel(excel_path, app_config.excel, limit=limit)


def _excel_load_limit(args: argparse.Namespace, has_prevented_filter: bool) -> int:
    """Return the safe Excel read limit before profile-level filters run."""
    if bool(getattr(args, "resume", False)) or has_prevented_filter:
        return 0
    return _order_item_limit(args)


def _prevented_items_path(args: argparse.Namespace) -> Path | None:
    """Return the configured prevented-items Excel path when one is enabled."""
    value = getattr(args, "prevented_items_excel", DEFAULT_PREVENTED_ITEMS_PATH)
    return Path(value) if value else None


def _reject_prevented_excel_as_order_source(
    excel_path: Path, prevented_path: Path | None
) -> None:
    """Stop accidental ordering from the prevented-items management file."""
    if prevented_path and is_prevented_items_excel_path(excel_path, prevented_path):
        raise SystemExit("Order Excel cannot be the prevented-items Excel file.")


def _prepared_order_items(
    profile_key: str, items: Iterable[Item], args: argparse.Namespace
) -> Iterable[Item]:
    """Yield one profile's remaining order items after session and resume checks."""
    require_state_file(profile_key)
    if not bool(getattr(args, "resume", False)):
        yield from items
        return
    processed_keys = _processed_summary_item_keys(profile_key, _summary_label(args))
    for item in items:
        if _item_key(item.code, item.name) not in processed_keys:
            yield item


def _limited_order_items(
    items: Iterable[Item], args: argparse.Namespace
) -> Iterable[Item]:
    """Apply the per-run item limit after prevented/resume filters."""
    limit = _order_item_limit(args)
    if limit <= 0:
        return items
    return itertools.islice(items, limit)


def _order_item_limit(args: argparse.Namespace) -> int:
    """Return the requested order item processing limit."""
    return int(getattr(args, "limit", 0) or 0)


def _match_only(args: argparse.Namespace) -> bool:
    """Return whether this order run should only evaluate product matches."""
    return bool(getattr(args, "match_only", False))


def _summary_label(args: argparse.Namespace) -> str:
    """Return the canonical summary label for the requested order mode."""
    if _match_only(args):
        return MATCH_ONLY_SUMMARY_LABEL
    return "order_item_summary"


def _processed_summary_item_keys(
    profile_key: str, summary_label: str = "order_item_summary"
) -> set[tuple[str, str]]:
    """Return item keys already written to the active profile summary."""
    summary_path = _latest_summary_path(profile_key, summary_label)
    if summary_path is None:
        return set()
    with summary_path.open("r", encoding="utf-8", newline="") as summary_file:
        reader = csv.DictReader(summary_file)
        return {
            _item_key(row.get("item_code", ""), row.get("item_name", ""))
            for row in reader
        }


def _latest_summary_path(profile_key: str, summary_label: str) -> Path | None:
    """Return the newest summary path from active, command, or legacy layouts."""
    active = current_artifact_run()
    paths: list[Path] = []
    if active:
        paths.extend(active.directory.glob(f"{summary_label}*.csv"))
    paths.extend(Path("artifacts/order").glob(f"{profile_key}/*/{summary_label}*.csv"))
    paths.append(Path("artifacts") / profile_key / f"{summary_label}.csv")
    paths.extend(Path("artifacts/legacy").glob(f"{profile_key}/*/{summary_label}.csv"))
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def _item_key(code: object, name: object) -> tuple[str, str]:
    """Return a stable key for matching Excel items to summary rows."""
    normalized_code = str(code or "").strip().lower()
    normalized_name = str(name or "").strip().lower()
    if normalized_code in {"", "nan", "none"}:
        normalized_code = ""
    return normalized_code, normalized_name


def _order_bot(
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
        **_order_bot_options(args),
    )


def _order_bot_options(args: argparse.Namespace) -> dict[str, object]:
    stop_flag = getattr(args, "stop_flag", None)
    return {
        "debug_browser": bool(getattr(args, "debug_browser", False)),
        "stop_flag_path": Path(stop_flag) if stop_flag else None,
        "fast_search": bool(getattr(args, "fast_search", False)),
        "match_only": _match_only(args),
        "order_ai_settings": order_ai_settings(args),
        "execution_mode": str(getattr(args, "execution_mode", "auto")),
        "matching_risk_policy": str(getattr(args, "matching_risk_policy", "safe")),
        "flagged_match_action": str(
            getattr(args, "flagged_match_action", "manual-review-only")
        ),
    }


def _run_profile_order(
    base_url: str, profile_key: str, bot: TawreedBot, items: Iterable[Item]
) -> None:
    """Run one profile order flow and handle session-expiry failures uniformly."""
    try:
        bot.place_order_from_items(items)
    except TawreedApiUnavailable as error:
        raise api_unavailable_exit(profile_key, error) from error
    except SessionInvalidError as error:
        raise invalid_session_exit(base_url, profile_key, error) from error


def _run_profile_match_only(
    base_url: str, profile_key: str, bot: TawreedBot, items: Iterable[Item]
) -> None:
    """Run product matching only and handle session-expiry failures uniformly."""
    try:
        bot.match_items_only(items)
    except TawreedApiUnavailable as error:
        raise api_unavailable_exit(profile_key, error) from error
    except SessionInvalidError as error:
        raise invalid_session_exit(base_url, profile_key, error) from error


def _run_parallel_order(
    app_config: AppConfig,
    profile_key: str,
    items,
    args: argparse.Namespace,
    item_workers: int,
) -> None:
    """Split items across multiprocessing workers and merge results."""
    from .item_worker_runner import run_order_chunk

    materialized = list(items)
    chunks = split_into_chunks(materialized, item_workers)
    payloads = _build_order_payloads(profile_key, chunks, args)
    print(f"[{profile_key}] Launching {len(chunks)} parallel item workers...")
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(processes=len(chunks)) as pool:
        results = pool.map(run_order_chunk, payloads)
    _merge_order_worker_outputs(profile_key, args)
    report_worker_results(app_config.base_url, profile_key, results)


def _merge_order_worker_outputs(profile_key: str, args: argparse.Namespace) -> None:
    """Merge all order worker output partitions for the active run."""
    merge_worker_summaries(profile_key, _summary_label(args))
    merge_order_worker_artifacts(
        profile_key, ("order_item_summary", "order_ai_trace", "manual_review")
    )


def _build_order_payloads(
    profile_key: str,
    chunks: list[list[Any]],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    """Build serializable payloads for each order worker."""
    config_path = str(Path(getattr(args, "config", "config.yaml")))
    options = _worker_options(args)
    return [
        {
            "config_path": config_path,
            "profile_key": profile_key,
            "items": [(it.code, it.name, it.qty) for it in chunk],
            "worker_id": idx,
            "options": options,
        }
        for idx, chunk in enumerate(chunks)
    ]


def _worker_options(args: argparse.Namespace) -> dict[str, Any]:
    """Extract serializable worker options from the CLI namespace."""
    run = current_artifact_run()
    return {
        "artifact_command": run.command if run else "",
        "artifact_run_id": run.run_id if run else "",
        "order_ai_settings": order_ai_settings(args),
        "debug_browser": bool(getattr(args, "debug_browser", False)),
        "fast_search": bool(getattr(args, "fast_search", False)),
        "match_only": _match_only(args),
        "execution_mode": str(getattr(args, "execution_mode", "auto")),
        "matching_risk_policy": str(getattr(args, "matching_risk_policy", "safe")),
        "flagged_match_action": str(
            getattr(args, "flagged_match_action", "manual-review-only")
        ),
        "stop_flag": getattr(args, "stop_flag", None),
        "warehouse_mode": getattr(args, "warehouse_mode", None),
        "min_discount_percent": getattr(args, "min_discount_percent", None),
    }
