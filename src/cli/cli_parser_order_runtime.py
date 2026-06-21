"""Runtime CLI arguments for the ordering subcommand."""

from __future__ import annotations

import argparse


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
