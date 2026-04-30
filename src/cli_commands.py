"""CLI command runners for Tawreed authentication and ordering workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config_models import AppConfig, ProfileConfig
from .excel import load_items_from_excel
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
        bot = build_bot(
            app_config,
            profile_key,
            profile,
            debug_browser=bool(getattr(args, "debug_browser", False)),
        )
        try:
            bot.place_order_from_items(items)
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
    return load_items_from_excel(excel_path, app_config.excel, limit=args.limit)


def build_bot(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    debug_browser: bool = False,
) -> TawreedBot:
    """Create a Tawreed bot instance for one profile."""
    return TawreedBot(
        config=app_config,
        profile_key=profile_key,
        profile=profile,
        state_path=state_path(profile_key),
        debug_browser=debug_browser,
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
