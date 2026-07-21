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
from .cli_parser_match import (
    build_match_products_parser,
    _add_match_input_arguments,
    _add_match_range_arguments,
    _add_match_ai_arguments,
    _add_match_ai_policy_arguments,
    _add_match_ai_provider_arguments,
)
from .cli_parser_other import (
    build_auth_parser,
    build_export_products_parser,
    _add_export_arguments,
    _add_export_output_arguments,
    _add_export_runtime_arguments,
)


# ============================================================================
# Main parser builder
# ============================================================================


def build_parser() -> argparse.ArgumentParser:
    """Build the main CLI argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description="Tawreed authentication, ordering, and exports CLI"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Minimum log level emitted to console (default: INFO).",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress console output below WARNING. Files are still written.",
    )
    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Emit log records as JSON (useful for CI / log aggregators).",
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
    # Match builders
    "build_match_products_parser",
    "_add_match_input_arguments",
    "_add_match_range_arguments",
    "_add_match_ai_arguments",
    "_add_match_ai_policy_arguments",
    "_add_match_ai_provider_arguments",
    # Other builders
    "build_auth_parser",
    "build_export_products_parser",
    "_add_export_arguments",
    "_add_export_output_arguments",
    "_add_export_runtime_arguments",
    # Main builder
    "build_parser",
]
