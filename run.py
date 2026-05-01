"""CLI entry point for Tawreed authentication and ordering workflows."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from src.cli_commands import run_auth_command, run_order_command, run_remove_cart_command
from src.cli_parser import build_parser
from src.config import load_config


def main() -> int:
    """Run the CLI command requested by the user."""
    load_dotenv()
    args = build_parser().parse_args()
    config_path = Path(args.config)
    app_config = load_config(config_path)
    if args.cmd == "auth":
        return run_auth_command(app_config, args)
    if args.cmd == "order":
        return run_order_command(app_config, args)
    if args.cmd == "remove-cart":
        return run_remove_cart_command(app_config, args)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
