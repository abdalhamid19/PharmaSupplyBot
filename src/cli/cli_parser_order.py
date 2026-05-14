"""CLI parser construction for the ordering subcommand."""

from __future__ import annotations

import argparse

from .cli_parser_ai import add_order_ai_arguments
from .cli_parser_shared import add_common_arguments, add_excel_argument


def build_order_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the order subcommand."""
    order_parser = subparsers.add_parser(
        "order",
        help="Create orders from Excel (no human interaction)",
    )
    add_common_arguments(order_parser)
    add_excel_argument(order_parser, "order", "data/input/order_items/")
    _add_order_runtime_arguments(order_parser)
    add_order_ai_arguments(order_parser)
    _add_order_filter_arguments(order_parser)


def _add_order_runtime_arguments(argument_parser: argparse.ArgumentParser) -> None:
    """Add order-run arguments that control execution behavior."""
    argument_parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of items (0 = no limit)",
    )
    argument_parser.add_argument(
        "--debug-browser",
        action="store_true",
        help="Open a visible browser for this order run",
    )
    argument_parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of parallel profiles (0 = unlimited)",
    )
    argument_parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip items already present in the active summary CSV",
    )
    argument_parser.add_argument(
        "--stop-flag",
        default=None,
        help="Path to a stop-request flag file checked between items",
    )
    argument_parser.add_argument(
        "--fast-search",
        action="store_true",
        help="Stop after the first acceptable product match",
    )
    argument_parser.add_argument(
        "--match-only",
        action="store_true",
        help="Only run product matching and never add matched items to the cart",
    )
    argument_parser.add_argument(
        "--execution-mode",
        choices=["auto", "api", "browser"],
        default="auto",
        help="Use Tawreed API when available, strict API only, or browser automation",
    )
    argument_parser.add_argument(
        "--item-workers",
        type=int,
        default=None,
        help="Parallel worker processes for items within one profile (overrides config)",
    )



def _add_order_filter_arguments(argument_parser: argparse.ArgumentParser) -> None:
    """Add order-run arguments that influence warehouse and prevented-item filtering."""
    argument_parser.add_argument(
        "--warehouse-mode",
        choices=["first_available", "max_available", "max_discount"],
        default=None,
        help="Override warehouse selection mode for this order run",
    )
    argument_parser.add_argument(
        "--min-discount-percent",
        type=float,
        default=None,
        help="Only select stores with discount percent greater than or equal to this value",
    )
    argument_parser.add_argument(
        "--prevented-items-excel",
        default="data/input/prevented_items/drugprevented.xlsx",
        help="Path to XLSX file containing items that must not be ordered",
    )
