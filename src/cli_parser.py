"""CLI parser construction for Tawreed authentication and ordering commands."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser and its subcommands."""
    parser = argparse.ArgumentParser(prog="PharmaSupplyBot")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    _build_auth_parser(subparsers)
    _build_order_parser(subparsers)
    return parser


def _build_auth_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the auth subcommand."""
    auth_parser = subparsers.add_parser("auth", help="Manual login once, save session state")
    _add_common_arguments(auth_parser)
    auth_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run a headless login using TAWREED_EMAIL and TAWREED_PASSWORD",
    )
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
        help="Path to order Excel file, usually under input/order_items/",
    )
    order_parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of items (0 = no limit)",
    )
    order_parser.add_argument(
        "--debug-browser",
        action="store_true",
        help="Open a visible browser for this order run",
    )
    order_parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip items already present in order_result_summary.csv for the selected profile",
    )
    order_parser.add_argument(
        "--stop-flag",
        default=None,
        help="Path to a stop-request flag file checked between items",
    )
    order_parser.add_argument(
        "--warehouse-mode",
        choices=["first_available", "max_available", "max_discount"],
        default=None,
        help="Override warehouse selection mode for this order run",
    )
    order_parser.add_argument(
        "--min-discount-percent",
        type=float,
        default=None,
        help="Only select stores with discount percent greater than or equal to this value",
    )
    order_parser.add_argument(
        "--prevented-items-excel",
        default="input/prevented_items/drugprevented.xlsx",
        help="Path to XLSX file containing items that must not be ordered",
    )


def _add_common_arguments(argument_parser: argparse.ArgumentParser) -> None:
    """Add CLI arguments shared by the auth and order commands."""
    argument_parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
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
