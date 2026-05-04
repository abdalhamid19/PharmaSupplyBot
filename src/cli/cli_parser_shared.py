"""Shared helpers for constructing CLI argument parsers."""

from __future__ import annotations

import argparse


def add_common_arguments(argument_parser: argparse.ArgumentParser) -> None:
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


def add_excel_argument(
    argument_parser: argparse.ArgumentParser,
    label: str,
    default_directory: str,
) -> None:
    """Add the required Excel-path argument for one CLI command."""
    argument_parser.add_argument(
        "--excel",
        required=True,
        help=f"Path to {label} Excel file, usually under {default_directory}",
    )
