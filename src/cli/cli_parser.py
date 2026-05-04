"""CLI parser construction for Tawreed authentication and ordering commands."""

from __future__ import annotations

import argparse

from .cli_parser_auth import build_auth_parser
from .cli_parser_cart import build_remove_cart_parser
from .cli_parser_order import build_order_parser


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser and its subcommands."""
    parser = argparse.ArgumentParser(prog="PharmaSupplyBot")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    build_auth_parser(subparsers)
    build_order_parser(subparsers)
    build_remove_cart_parser(subparsers)
    return parser
