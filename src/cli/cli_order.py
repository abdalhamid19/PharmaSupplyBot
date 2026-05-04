"""CLI command runner for Tawreed ordering workflows."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.utils.excel import load_items_from_excel
from ..core.prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    filter_prevented_order_items,
    is_prevented_items_excel_path,
    load_prevented_items,
)
from ..tawreed.tawreed import TawreedBot
from ..tawreed.tawreed_session import SessionInvalidError
from .cli_shared import build_bot, invalid_session_exit, require_state_file


def run_order_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Place orders from Excel for the selected profiles."""
    _apply_order_overrides(app_config, args)
    items = _load_order_items(app_config, args)
    if not items:
        print("No items found from Excel (after filtering).")
        return 0

    profiles = app_config.profiles_to_run(profile=args.profile, all_profiles=args.all_profiles)
    for profile_key, profile in profiles:
        profile_items = _prepared_order_items(profile_key, items, args)
        if not profile_items:
            print(f"[{profile_key}] No remaining items to process.")
            continue
        bot = _order_bot(app_config, profile_key, profile, args)
        _run_profile_order(app_config.base_url, profile_key, bot, profile_items)
    return 0


def _apply_order_overrides(app_config: AppConfig, args: argparse.Namespace) -> None:
    """Apply optional per-run order settings to the loaded application config."""
    warehouse_mode = getattr(args, "warehouse_mode", None)
    if warehouse_mode:
        app_config.warehouse_strategy["mode"] = str(warehouse_mode)
    min_discount_percent = getattr(args, "min_discount_percent", None)
    if min_discount_percent is not None:
        app_config.warehouse_strategy["min_discount_percent"] = float(min_discount_percent)


def _load_order_items(app_config: AppConfig, args: argparse.Namespace):
    """Load the order items requested by the CLI command."""
    excel_path = Path(args.excel)
    prevented_path = _prevented_items_path(args)
    if prevented_path and is_prevented_items_excel_path(excel_path, prevented_path):
        raise SystemExit(
            f"Order Excel cannot be the prevented-items file: {excel_path}. "
            "Choose the shortage/order Excel file instead."
        )
    items = load_items_from_excel(excel_path, app_config.excel, limit=args.limit)
    if not prevented_path:
        return items
    if not prevented_path.is_file():
        print(f"Prevented-items Excel not found: {prevented_path}. Continuing without it.")
        return items
    prevented_items = load_prevented_items(prevented_path)
    allowed_items, skipped_count = filter_prevented_order_items(items, prevented_items)
    if skipped_count:
        print(f"Skipped {skipped_count} prevented items from {prevented_path}.")
    return allowed_items


def _prevented_items_path(args: argparse.Namespace) -> Path | None:
    """Return the configured prevented-items Excel path when one is enabled."""
    value = getattr(args, "prevented_items_excel", DEFAULT_PREVENTED_ITEMS_PATH)
    return Path(value) if value else None


def _prepared_order_items(profile_key: str, items: list, args: argparse.Namespace) -> list:
    """Return one profile's remaining order items after session and resume checks."""
    require_state_file(profile_key)
    if not bool(getattr(args, "resume", False)):
        return items
    processed_keys = _processed_summary_item_keys(profile_key)
    return [item for item in items if _item_key(item.code, item.name) not in processed_keys]


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
    )


def _run_profile_order(base_url: str, profile_key: str, bot: TawreedBot, items: list) -> None:
    """Run one profile order flow and handle session-expiry failures uniformly."""
    try:
        bot.place_order_from_items(items)
    except SessionInvalidError as error:
        raise invalid_session_exit(base_url, profile_key, error) from error
