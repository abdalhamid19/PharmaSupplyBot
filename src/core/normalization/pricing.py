"""Local price parsing helpers used by deterministic indexing."""

from __future__ import annotations

import re


def parse_price(value) -> float | None:
    """Parse a positive price from CSV-like values."""
    if value in (None, ""):
        return None
    text = re.sub(r"[^\d.]", "", str(value).strip())
    if not text:
        return None
    try:
        price = float(text)
    except ValueError:
        return None
    return price if price > 0 else None
