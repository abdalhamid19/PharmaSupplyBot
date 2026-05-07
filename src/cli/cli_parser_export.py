"""CLI parser construction for Tawreed product catalog exports."""

from __future__ import annotations

import argparse

from .cli_parser_shared import add_common_arguments


def build_export_products_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the export-products subcommand."""
    export_parser = subparsers.add_parser(
        "export-products",
        help="Export all Tawreed store products to CSV, XLSX, and TXT",
    )
    add_common_arguments(export_parser)
    _add_export_arguments(export_parser)


def _add_export_arguments(argument_parser: argparse.ArgumentParser) -> None:
    _add_export_output_arguments(argument_parser)
    _add_export_runtime_arguments(argument_parser)


def _add_export_output_arguments(argument_parser: argparse.ArgumentParser) -> None:
    argument_parser.add_argument(
        "--output-dir",
        default="artifacts/{profile}",
        help="Directory for export files; {profile} is replaced with profile key",
    )
    argument_parser.add_argument(
        "--stem",
        default="tawreed_products",
        help="Output filename without extension",
    )


def _add_export_runtime_arguments(argument_parser: argparse.ArgumentParser) -> None:
    argument_parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Tawreed API page size used while exporting products",
    )
    argument_parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum rows to export for testing (0 = all Tawreed products)",
    )
    argument_parser.add_argument(
        "--debug-browser",
        action="store_true",
        help="Open a visible browser for this export run",
    )
