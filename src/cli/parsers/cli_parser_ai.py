"""AI matching CLI parser helpers."""

from __future__ import annotations

import argparse


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


__all__ = [
    "add_order_ai_arguments",
    "_add_ai_policy_arguments",
]
