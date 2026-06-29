"""Unified CLI parser construction for all subcommands - re-exports from split modules."""

from __future__ import annotations

import argparse

# Re-export from split modules
from .cli_parser_shared import add_common_arguments, add_excel_argument
from .cli_parser_ai import add_order_ai_arguments, _add_ai_policy_arguments
from .cli_parser_risk import add_matching_risk_arguments
from .cli_parser_manual import (
    add_manual_review_removal_arguments,
    add_manual_review_search_argument,
)
from .cli_parser_order import (
    add_order_runtime_arguments,
    _add_order_limits_and_debug,
    _add_order_range_arguments,
    _add_order_resume_arguments,
    _add_order_execution_arguments,
    build_order_parser,
    _add_order_filter_arguments,
    build_remove_cart_parser,
    _add_remove_cart_runtime_arguments,
    _add_debug_browser_argument,
    _add_execution_mode_argument,
)


# ============================================================================
# Auth subcommand
# ============================================================================


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


# ============================================================================
# Export subcommand
# ============================================================================


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


# ============================================================================
# Match products subcommand
# ============================================================================


def build_match_products_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the match-products subcommand."""
    parser = subparsers.add_parser(
        "match-products",
        help="Match an inventory Excel/CSV file against exported Tawreed products",
    )
    add_common_arguments(parser)
    _add_match_input_arguments(parser)
    _add_match_range_arguments(parser)
    _add_match_ai_arguments(parser)


def _add_match_input_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--excel", required=True, help="Inventory Excel or CSV file")
    parser.add_argument("--tawreed-csv", default=None, help="Tawreed products CSV")
    parser.add_argument("--output", default=None, help="Output CSV path")


def _add_match_range_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--trace", action="store_true")


def _add_match_ai_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--no-ai", action="store_true")
    parser.add_argument("--threshold", type=int, default=80)
    parser.add_argument("--ai-threshold", type=float, default=90.0)
    _add_match_ai_policy_arguments(parser)
    _add_match_ai_provider_arguments(parser)


def _add_match_ai_policy_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--ai-verify-policy",
        choices=["score", "fuzzy", "all-non-exact", "all"],
        default="score",
    )
    parser.add_argument(
        "--ai-search-policy",
        choices=["safe", "review-candidates", "expanded", "aggressive"],
        default="review-candidates",
    )


def _add_match_ai_provider_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--review-model", default=None)
    parser.add_argument("--concurrency", type=int, default=None)
    parser.add_argument("--ai-search-limit", type=int, default=None)
    parser.add_argument("--no-ai-preflight", action="store_true")
    parser.add_argument("--rotation-preflight-policy", default="smart")


# ============================================================================
# Main parser builder
# ============================================================================


def build_parser() -> argparse.ArgumentParser:
    """Build the main CLI argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description="Tawreed authentication, ordering, and exports CLI"
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    build_auth_parser(subparsers)
    build_order_parser(subparsers)
    build_remove_cart_parser(subparsers)
    build_export_products_parser(subparsers)
    build_match_products_parser(subparsers)
    return parser


__all__ = [
    # Re-exports
    "add_common_arguments",
    "add_excel_argument",
    "add_order_ai_arguments",
    "_add_ai_policy_arguments",
    "add_matching_risk_arguments",
    "add_manual_review_removal_arguments",
    "add_manual_review_search_argument",
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
    # Main builders
    "build_auth_parser",
    "build_export_products_parser",
    "_add_export_arguments",
    "_add_export_output_arguments",
    "_add_export_runtime_arguments",
    "build_match_products_parser",
    "_add_match_input_arguments",
    "_add_match_range_arguments",
    "_add_match_ai_arguments",
    "_add_match_ai_policy_arguments",
    "_add_match_ai_provider_arguments",
    "build_parser",
]
