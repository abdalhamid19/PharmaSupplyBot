"""CLI parser construction for the cart-removal subcommand."""

from __future__ import annotations

import argparse

from .cli_parser_manual_review import add_manual_review_removal_arguments
from .cli_parser_shared import add_common_arguments


def build_remove_cart_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the remove-cart subcommand."""
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
