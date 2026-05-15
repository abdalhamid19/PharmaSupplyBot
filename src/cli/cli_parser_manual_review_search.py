"""CLI parser helpers for manual-review corrected-item search."""

from __future__ import annotations

import argparse


def add_manual_review_search_argument(argument_parser: argparse.ArgumentParser) -> None:
    """Add manual-review correction source control to order."""
    argument_parser.add_argument(
        "--from-manual-review-corrections",
        default=None,
        help="Manual-review CSV whose corrected rows should be searched match-only",
    )
