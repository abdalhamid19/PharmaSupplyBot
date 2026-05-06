"""CLI command runner for Tawreed ordering workflows."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import itertools
import multiprocessing
from pathlib import Path
from typing import Any, Iterable

from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    filter_prevented_order_items,
    is_prevented_items_excel_path,
    load_prevented_items,
)
from ..core.utils.chunking import split_into_chunks
from ..core.utils.excel import Item, load_items_from_excel
from ..tawreed.order_result_merger import merge_worker_summaries
from ..tawreed.tawreed import TawreedBot
from ..tawreed.tawreed_session import SessionInvalidError
from .cli_shared import build_bot, invalid_session_exit, require_state_file
from .item_worker_pool import report_worker_results, resolve_item_workers


def run_order_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Place orders from Excel for the selected profiles."""
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
    _run_profile_order(app_config.base_url, profile_key, bot, profile_items)


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
    excel_path = Path(args.excel)
    prevented_path = _prevented_items_path(args)
    _reject_prevented_excel_as_order_source(excel_path, prevented_path)
    has_prevented_filter = bool(prevented_path and prevented_path.is_file())
    items = load_items_from_excel(
        excel_path,
        app_config.excel,
        limit=_excel_load_limit(args, has_prevented_filter),
    )
    if has_prevented_filter and prevented_path is not None:
        prevented_items = load_prevented_items(prevented_path)
        items = filter_prevented_order_items(items, prevented_items)
    return items


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
    processed_keys = _processed_summary_item_keys(profile_key)
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


def _processed_summary_item_keys(profile_key: str) -> set[tuple[str, str]]:
    """Return item keys already written to the profile order summary."""
    summary_path = Path("artifacts") / profile_key / "order_result_summary.csv"
    if not summary_path.exists():
        return set()
    with summary_path.open("r", encoding="utf-8", newline="") as summary_file:
        reader = csv.DictReader(summary_file)
        return {
            _item_key(row.get("item_code", ""), row.get("item_name", ""))
            for row in reader
        }


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
    stop_flag = getattr(args, "stop_flag", None)
    return build_bot(
        app_config,
        profile_key,
        profile,
        debug_browser=bool(getattr(args, "debug_browser", False)),
        stop_flag_path=Path(stop_flag) if stop_flag else None,
        fast_search=bool(getattr(args, "fast_search", False)),
    )


def _run_profile_order(
    base_url: str, profile_key: str, bot: TawreedBot, items: Iterable[Item]
) -> None:
    """Run one profile order flow and handle session-expiry failures uniformly."""
    try:
        bot.place_order_from_items(items)
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
    merge_worker_summaries(profile_key, "order_result_summary")
    report_worker_results(app_config.base_url, profile_key, results)


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
    return {
        "debug_browser": bool(getattr(args, "debug_browser", False)),
        "fast_search": bool(getattr(args, "fast_search", False)),
        "stop_flag": getattr(args, "stop_flag", None),
        "warehouse_mode": getattr(args, "warehouse_mode", None),
        "min_discount_percent": getattr(args, "min_discount_percent", None),
    }
