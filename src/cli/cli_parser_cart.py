"""CLI parser construction for the cart-removal subcommand."""

from __future__ import annotations

import argparse

from .cli_parser_shared import add_common_arguments, add_excel_argument


def build_remove_cart_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the remove-cart subcommand."""
    remove_parser = subparsers.add_parser(
        "remove-cart",
        help="Remove matching products from Tawreed carts",
    )
    add_common_arguments(remove_parser)
    add_excel_argument(remove_parser, "cart-removal", "data/input/remove_items/")
    _add_remove_cart_runtime_arguments(remove_parser)


def _add_remove_cart_runtime_arguments(
    argument_parser: argparse.ArgumentParser,
) -> None:
    """Add remove-cart runtime-control arguments."""
    argument_parser.add_argument(
        "--debug-browser",
        action="store_true",
        help="Open a visible browser for this cart-removal run",
    )
    argument_parser.add_argument(
        "--stop-flag",
        default=None,
        help="Path to a stop-request flag file checked between cart-removal items",
    )
    argument_parser.add_argument(
        "--item-workers",
        type=int,
        default=None,
        help="Parallel worker processes for items within one profile",
    )
