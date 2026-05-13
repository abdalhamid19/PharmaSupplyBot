"""CLI parser construction for standalone product matching."""

from __future__ import annotations

import argparse

from .cli_parser_shared import add_common_arguments


def build_match_products_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the match-products subcommand."""
    parser = subparsers.add_parser(
        "match-products",
        help="Match an inventory Excel/CSV file against exported Tawreed products",
    )
    add_common_arguments(parser)
    parser.add_argument("--excel", required=True, help="Inventory Excel or CSV file")
    parser.add_argument("--tawreed-csv", default=None, help="Tawreed products CSV")
    parser.add_argument("--output", default=None, help="Output CSV path")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--no-ai", action="store_true")
    parser.add_argument("--threshold", type=int, default=80)
    parser.add_argument("--ai-threshold", type=float, default=90.0)
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
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--review-model", default=None)
    parser.add_argument("--concurrency", type=int, default=None)
    parser.add_argument("--ai-search-limit", type=int, default=None)
    parser.add_argument("--no-ai-preflight", action="store_true")
    parser.add_argument("--rotation-preflight-policy", default="smart")
