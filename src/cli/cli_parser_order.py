"""CLI parser builders for order and cart subcommands."""

from __future__ import annotations

import argparse

from .cli_parser_manual import add_manual_review_removal_arguments


# ============================================================================
# Order runtime helpers
# ============================================================================


def add_order_runtime_arguments(argument_parser: argparse.ArgumentParser) -> None:
    """Add order-run arguments that control execution behavior."""
    _add_order_limits_and_debug(argument_parser)
    _add_order_range_arguments(argument_parser)
    _add_order_resume_arguments(argument_parser)
    _add_order_execution_arguments(argument_parser)


def _add_order_limits_and_debug(argument_parser: argparse.ArgumentParser) -> None:
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


def _add_order_range_arguments(argument_parser: argparse.ArgumentParser) -> None:
    argument_parser.add_argument(
        "--start-item",
        type=int,
        default=1,
        help="Start processing from this item number in the Excel sheet",
    )
    argument_parser.add_argument(
        "--end-item",
        type=int,
        default=0,
        help="Stop processing after this item number in the Excel sheet (0 = end of sheet)",
    )


def _add_order_resume_arguments(argument_parser: argparse.ArgumentParser) -> None:
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


def _add_order_execution_arguments(argument_parser: argparse.ArgumentParser) -> None:
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


# ============================================================================
# Order subcommand
# ============================================================================


def build_order_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the order subcommand."""
    from .cli_parser_shared import add_common_arguments, add_excel_argument
    from .cli_parser_ai import add_order_ai_arguments
    from .cli_parser_risk import add_matching_risk_arguments
    from .cli_parser_manual import add_manual_review_search_argument

    order_parser = subparsers.add_parser(
        "order",
        help="Create orders from Excel (no human interaction)",
    )
    add_common_arguments(order_parser)
    add_excel_argument(order_parser, "order", "data/input/order_items/")
    add_order_runtime_arguments(order_parser)
    add_matching_risk_arguments(order_parser)
    add_order_ai_arguments(order_parser)
    _add_order_filter_arguments(order_parser)
    add_manual_review_search_argument(order_parser)


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


# ============================================================================
# Remove cart subcommand
# ============================================================================


def build_remove_cart_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the remove-cart subcommand."""
    from .cli_parser_shared import add_common_arguments

    remove_parser = subparsers.add_parser(
        "remove-cart",
        help="Remove matching products from Tawreed carts",
    )
    add_common_arguments(remove_parser)
    remove_parser.add_argument(
        "--excel",
        default=None,
        help="Path to cart-removal Excel file, usually under data/input/remove_items/",
    )
    _add_remove_cart_runtime_arguments(remove_parser)


def _add_remove_cart_runtime_arguments(
    argument_parser: argparse.ArgumentParser,
) -> None:
    """Add remove-cart runtime-control arguments."""
    _add_debug_browser_argument(argument_parser)
    argument_parser.add_argument(
        "--stop-flag",
        default=None,
        help="Path to a stop-request flag file checked between cart-removal items",
    )
    _add_execution_mode_argument(argument_parser)
    argument_parser.add_argument(
        "--item-workers",
        type=int,
        default=None,
        help="Parallel worker processes for items within one profile",
    )
    add_manual_review_removal_arguments(argument_parser)


def _add_debug_browser_argument(argument_parser: argparse.ArgumentParser) -> None:
    """Add the cart-removal debug browser flag."""
    argument_parser.add_argument(
        "--debug-browser",
        action="store_true",
        help="Open a visible browser for this cart-removal run",
    )


def _add_execution_mode_argument(argument_parser: argparse.ArgumentParser) -> None:
    """Add the shared API/browser backend selector."""
    argument_parser.add_argument(
        "--execution-mode",
        choices=["auto", "api", "browser"],
        default="auto",
        help="Use Tawreed API when available, strict API only, or browser automation",
    )


__all__ = [
    "add_order_runtime_arguments",
    "_add_order_limits_and_debug",
    "_add_order_range_arguments",
    "_add_order_resume_arguments",
    "_add_order_execution_arguments",
    "build_order_parser",
    "_add_order_filter_arguments",
    "build_remove_cart_parser",
    "_add_remove_cart_runtime_arguments",
    "_add_debug_browser_argument",
    "_add_execution_mode_argument",
]
