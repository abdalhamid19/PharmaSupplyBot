"""Unified CLI parser construction for all subcommands."""

from __future__ import annotations

import argparse


# ============================================================================
# Shared helpers
# ============================================================================


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
        required=False,
        help=f"Path to {label} Excel file, usually under {default_directory}",
    )


# ============================================================================
# AI matching helpers
# ============================================================================


def add_order_ai_arguments(argument_parser: argparse.ArgumentParser) -> None:
    """Add opt-in live-order AI matching controls."""
    argument_parser.add_argument(
        "--ai", action="store_true", help="Enable active AI matching"
    )
    argument_parser.add_argument("--provider", default=None)
    argument_parser.add_argument("--model", default=None)
    argument_parser.add_argument("--api-key", default=None)
    argument_parser.add_argument("--review-model", default=None)
    argument_parser.add_argument("--concurrency", type=int, default=None)
    _add_ai_policy_arguments(argument_parser)
    argument_parser.add_argument("--ai-accept-confidence", type=float, default=0.9)
    argument_parser.add_argument(
        "--ai-verify-soft-accept-confidence", type=float, default=0.8
    )
    argument_parser.add_argument("--ai-review-threshold", type=float, default=0.95)
    argument_parser.add_argument("--no-ai-preflight", action="store_true")
    argument_parser.add_argument("--rotation-preflight-policy", default="smart")


def _add_ai_policy_arguments(argument_parser: argparse.ArgumentParser) -> None:
    argument_parser.add_argument(
        "--ai-verify-policy",
        choices=["score", "fuzzy", "all-non-exact", "all"],
        default="score",
    )
    argument_parser.add_argument(
        "--ai-search-policy",
        choices=["safe", "review-candidates", "expanded", "aggressive"],
        default="review-candidates",
    )


# ============================================================================
# Matching risk helpers
# ============================================================================


def add_matching_risk_arguments(argument_parser: argparse.ArgumentParser) -> None:
    """Add order-run controls for reviewable aggressive matching."""
    argument_parser.add_argument(
        "--matching-risk-policy",
        choices=["safe", "aggressive"],
        default="safe",
        help="Use safe matching only, or allow flagged aggressive matches",
    )
    argument_parser.add_argument(
        "--flagged-match-action",
        choices=["manual-review-only", "add-to-cart"],
        default="manual-review-only",
        help="Stage flagged aggressive matches or add them while marking manual review",
    )


# ============================================================================
# Manual review helpers
# ============================================================================


def add_manual_review_removal_arguments(argument_parser: argparse.ArgumentParser) -> None:
    """Add manual-review source controls to remove-cart."""
    argument_parser.add_argument(
        "--from-manual-review",
        default=None,
        help="Manual-review CSV whose not_matching rows should be removed",
    )
    argument_parser.add_argument(
        "--manual-review-scope",
        choices=["current-run", "saved-decisions"],
        default="current-run",
        help="Remove not_matching rows from one CSV or saved manual decisions",
    )
    argument_parser.add_argument(
        "--manual-decision",
        choices=["not_matching"],
        default="not_matching",
        help="Manual-review decision selected for cart removal",
    )


def add_manual_review_search_argument(argument_parser: argparse.ArgumentParser) -> None:
    """Add manual-review correction source control to order."""
    argument_parser.add_argument(
        "--from-manual-review-corrections",
        default=None,
        help="Manual-review CSV whose corrected rows should be searched match-only",
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
# Order runtime helpers
# ============================================================================


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


# ============================================================================
# Order subcommand
# ============================================================================


def build_order_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the order subcommand."""
    order_parser = subparsers.add_parser(
        "order",
        help="Create orders from Excel (no human interaction)",
    )
    add_common_arguments(order_parser)
    add_excel_argument(order_parser, "order", "data/input/order_items/")
    add_order_runtime_arguments(order_parser)
    add_matching_risk_arguments(order_parser)
    add_order_ai_arguments(order_parser)
    _add_order_filter_arguments(order_parser)
    add_manual_review_search_argument(order_parser)


def _add_order_filter_arguments(argument_parser: argparse.ArgumentParser) -> None:
    """Add order-run arguments that influence warehouse and prevented-item filtering."""
    argument_parser.add_argument(
        "--warehouse-mode",
        choices=["first_available", "max_available", "max_discount"],
        default=None,
        help="Override warehouse selection mode for this order run",
    )
    argument_parser.add_argument(
        "--min-discount-percent",
        type=float,
        default=None,
        help="Only select stores with discount percent greater than or equal to this value",
    )
    argument_parser.add_argument(
        "--prevented-items-excel",
        default="data/input/prevented_items/drugprevented.xlsx",
        help="Path to XLSX file containing items that must not be ordered",
    )


# ============================================================================
# Remove cart subcommand
# ============================================================================


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
