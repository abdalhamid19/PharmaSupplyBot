"""Resolve remove-cart input sources for CLI runs."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.core.manual_review.manual_review_removal import (
    cart_items_from_manual_review_csv,
    cart_items_from_saved_not_matching,
)


def cart_removal_items(args: argparse.Namespace, excel_loader) -> list:
    """Return cart-removal items from Excel or manual-review decisions."""
    if getattr(args, "manual_review_scope", "") == "saved-decisions":
        return cart_items_from_saved_not_matching()
    manual_review = getattr(args, "from_manual_review", None)
    if manual_review:
        return cart_items_from_manual_review_csv(Path(manual_review))
    excel = getattr(args, "excel", None)
    if not excel:
        raise SystemExit("Provide --excel or --from-manual-review.")
    return list(excel_loader(Path(excel)))
