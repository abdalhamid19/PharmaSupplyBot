"""CLI entry point for Tawreed authentication and ordering workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from src.config import load_config
from src.excel import load_items_from_excel
from src.tawreed import TawreedBot


def main() -> int:
    """Run the CLI command requested by the user."""
    load_dotenv()
    args = _build_parser().parse_args()
    config_path = Path(args.config)
    app_config = load_config(config_path)
    if args.cmd == "auth":
        return _run_auth_command(app_config, args)
    if args.cmd == "order":
        return _run_order_command(app_config, args)
    raise AssertionError("unreachable")


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser and its subcommands."""
    parser = argparse.ArgumentParser(prog="PharmaSupplyBot")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    _build_auth_parser(subparsers)
    _build_order_parser(subparsers)
    return parser


def _run_auth_command(app_config, args: argparse.Namespace) -> int:
    """Authenticate and persist session state for the selected profiles."""
    for profile_key, profile in _profiles_to_run(app_config, args):
        bot = _build_bot(app_config, profile_key, profile)
        bot.auth_interactive(wait_seconds=int(args.wait_seconds))
    return 0


def _run_order_command(app_config, args: argparse.Namespace) -> int:
    """Place orders from Excel for the selected profiles."""
    items = _load_order_items(app_config, args)
    if not items:
        print("No items found from Excel (after filtering).")
        return 0
    for profile_key, profile in _profiles_to_run(app_config, args):
        _require_state_file(profile_key)
        bot = _build_bot(app_config, profile_key, profile)
        bot.place_order_from_items(items)
    return 0


def _build_auth_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the auth subcommand."""
    auth_parser = subparsers.add_parser(
        "auth",
        help="Manual login once, save session state",
    )
    _add_common_arguments(auth_parser)
    auth_parser.add_argument(
        "--wait-seconds",
        type=int,
        default=600,
        help="How long to keep browser open waiting for login detection",
    )


def _build_order_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the order subcommand."""
    order_parser = subparsers.add_parser(
        "order",
        help="Create orders from Excel (no human interaction)",
    )
    _add_common_arguments(order_parser)
    order_parser.add_argument(
        "--excel",
        required=True,
        help="Path to Excel file in input/",
    )
    order_parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of items (0 = no limit)",
    )


def _profiles_to_run(app_config, args: argparse.Namespace):
    """Return the profiles selected by the CLI arguments."""
    return app_config.profiles_to_run(
        profile=args.profile,
        all_profiles=args.all_profiles,
    )


def _load_order_items(app_config, args: argparse.Namespace):
    """Load the order items requested by the CLI command."""
    excel_path = Path(args.excel)
    return load_items_from_excel(
        excel_path,
        app_config.excel,
        limit=args.limit,
    )


def _build_bot(app_config, profile_key: str, profile) -> TawreedBot:
    """Create a Tawreed bot instance for one profile."""
    return TawreedBot(
        config=app_config,
        profile_key=profile_key,
        profile=profile,
        state_path=_state_path(profile_key),
    )


def _require_state_file(profile_key: str) -> None:
    """Ensure the profile has a saved Playwright storage state file."""
    state_path = _state_path(profile_key)
    if state_path.exists():
        return
    raise SystemExit(
        f"Missing saved session state for profile '{profile_key}'. "
        f"Run: py run.py auth --profile {profile_key}"
    )


def _state_path(profile_key: str) -> Path:
    """Return the storage-state path for one profile."""
    state_dir = Path("state")
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{profile_key}.json"


def _add_common_arguments(argument_parser: argparse.ArgumentParser) -> None:
    """Add CLI arguments shared by the auth and order commands."""
    argument_parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml",
    )
    argument_parser.add_argument(
        "--profile",
        default=None,
        help="Profile key from config.yaml (e.g. wardany)",
    )
    argument_parser.add_argument(
        "--all-profiles",
        action="store_true",
        help="Run for all profiles in config.yaml",
    )


if __name__ == "__main__":
    raise SystemExit(main())

