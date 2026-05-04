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
    remove_parser.add_argument(
        "--debug-browser",
        action="store_true",
        help="Open a visible browser for this cart-removal run",
    )
