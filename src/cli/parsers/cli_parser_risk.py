"""Matching risk CLI parser helpers."""

from __future__ import annotations

import argparse


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


__all__ = [
    "add_matching_risk_arguments",
]
