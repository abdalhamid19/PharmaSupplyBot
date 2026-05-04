"""CLI parser construction for the authentication subcommand."""

from __future__ import annotations

import argparse

from .cli_parser_shared import add_common_arguments


def build_auth_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the auth subcommand."""
    auth_parser = subparsers.add_parser("auth", help="Manual login once, save session state")
    add_common_arguments(auth_parser)
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
