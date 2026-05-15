"""CLI parser construction for the ordering subcommand."""

from __future__ import annotations

import argparse

from .cli_parser_ai import add_order_ai_arguments
from .cli_parser_matching import add_matching_risk_arguments
from .cli_parser_manual_review_search import add_manual_review_search_argument
from .cli_parser_order_runtime import add_order_runtime_arguments
from .cli_parser_shared import add_common_arguments, add_excel_argument


def build_order_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the order subcommand."""
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
