"""CLI parser helpers for manual-review cart-removal sources."""

from __future__ import annotations

import argparse


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
