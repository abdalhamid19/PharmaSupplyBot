"""CLI command runners for Tawreed authentication and ordering workflows."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .config_models import AppConfig, ProfileConfig
from .excel import load_items_from_excel
from .prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    filter_prevented_order_items,
    load_prevented_items,
)
from .tawreed import TawreedBot
from .tawreed_session import SessionInvalidError, open_reauth_in_browser


def run_auth_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Authenticate and persist session state for the selected profiles."""
    for profile_key, profile in profiles_to_run(app_config, args):
        bot = build_bot(app_config, profile_key, profile)
        auth_runner = bot.auth_headless if bool(getattr(args, "headless", False)) else bot.auth_interactive
        auth_runner(wait_seconds=int(args.wait_seconds))
    return 0


def run_order_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Place orders from Excel for the selected profiles."""
    apply_order_overrides(app_config, args)
    items = load_order_items(app_config, args)
    if not items:
        print("No items found from Excel (after filtering).")
        return 0
    for profile_key, profile in profiles_to_run(app_config, args):
        require_state_file(profile_key)
        profile_items = resumable_order_items(profile_key, items, args)
        if not profile_items:
            print(f"[{profile_key}] No remaining items to process.")
            continue
        bot = build_bot(
            app_config,
            profile_key,
            profile,
            debug_browser=bool(getattr(args, "debug_browser", False)),
            stop_flag_path=stop_flag_path(args),
        )
        try:
            bot.place_order_from_items(profile_items)
        except SessionInvalidError as error:
            print(f"[{profile_key}] {error}")
            open_reauth_in_browser(app_config.base_url, profile_key)
            raise SystemExit(
                f"Session for profile '{profile_key}' is not valid. "
                f"Run: py run.py auth --profile {profile_key}"
            ) from error
    return 0


def apply_order_overrides(app_config: AppConfig, args: argparse.Namespace) -> None:
    """Apply optional per-run order settings to the loaded application config."""
    warehouse_mode = getattr(args, "warehouse_mode", None)
    if warehouse_mode:
        app_config.warehouse_strategy["mode"] = str(warehouse_mode)
    min_discount_percent = getattr(args, "min_discount_percent", None)
    if min_discount_percent is not None:
        app_config.warehouse_strategy["min_discount_percent"] = float(min_discount_percent)


def profiles_to_run(app_config: AppConfig, args: argparse.Namespace):
    """Return the profiles selected by the CLI arguments."""
    return app_config.profiles_to_run(profile=args.profile, all_profiles=args.all_profiles)


def load_order_items(app_config: AppConfig, args: argparse.Namespace):
    """Load the order items requested by the CLI command."""
    excel_path = Path(args.excel)
    items = load_items_from_excel(excel_path, app_config.excel, limit=args.limit)
    prevented_path_value = getattr(args, "prevented_items_excel", DEFAULT_PREVENTED_ITEMS_PATH)
    prevented_path = Path(prevented_path_value) if prevented_path_value else None
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


def resumable_order_items(profile_key: str, items: list, args: argparse.Namespace) -> list:
    """Return remaining order items when resume mode is enabled."""
    if not bool(getattr(args, "resume", False)):
        return items
    processed_keys = processed_summary_item_keys(profile_key)
    return [item for item in items if item_key(item.code, item.name) not in processed_keys]


def processed_summary_item_keys(profile_key: str) -> set[tuple[str, str]]:
    """Return item keys already written to the profile order summary."""
    summary_path = Path("artifacts") / profile_key / "order_result_summary.csv"
    if not summary_path.exists():
        return set()
    with summary_path.open("r", encoding="utf-8", newline="") as summary_file:
        reader = csv.DictReader(summary_file)
        return {
            item_key(row.get("item_code", ""), row.get("item_name", ""))
            for row in reader
        }


def item_key(code: object, name: object) -> tuple[str, str]:
    """Return a stable key for matching Excel items to summary rows."""
    normalized_code = str(code or "").strip().lower()
    normalized_name = str(name or "").strip().lower()
    if normalized_code in {"", "nan", "none"}:
        normalized_code = ""
    return normalized_code, normalized_name


def stop_flag_path(args: argparse.Namespace) -> Path | None:
    """Return the optional stop-request flag path."""
    value = getattr(args, "stop_flag", None)
    return Path(value) if value else None


def build_bot(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    debug_browser: bool = False,
    stop_flag_path: Path | None = None,
) -> TawreedBot:
    """Create a Tawreed bot instance for one profile."""
    return TawreedBot(
        config=app_config,
        profile_key=profile_key,
        profile=profile,
        state_path=state_path(profile_key),
        debug_browser=debug_browser,
        stop_flag_path=stop_flag_path,
    )


def require_state_file(profile_key: str) -> None:
    """Ensure the profile has a saved Playwright storage state file."""
    saved_state_path = state_path(profile_key)
    if saved_state_path.exists():
        return
    raise SystemExit(
        f"Missing saved session state for profile '{profile_key}'. "
        f"Run: py run.py auth --profile {profile_key}"
    )


def state_path(profile_key: str) -> Path:
    """Return the storage-state path for one profile."""
    state_dir = Path("state")
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{profile_key}.json"
