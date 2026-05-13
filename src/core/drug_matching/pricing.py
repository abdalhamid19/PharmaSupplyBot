"""Shared price parsing and formatting helpers."""
from __future__ import annotations

import re


def parse_price(value) -> float | None:
    """Parse a positive price from CSV-like values."""
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    text = re.sub(r"[^\d.]", "", text)
    if not text:
        return None
    try:
        price = float(text)
    except ValueError:
        return None
    return price if price > 0 else None


def format_price(value) -> str:
    """Format a parsed or raw price for compact prompt context."""
    price = parse_price(value)
    if price is None:
        return "-"
    return str(int(price)) if price.is_integer() else f"{price:.2f}".rstrip("0")


def price_delta_text(left, right) -> str:
    """Return percentage difference text, or '-' when either price is missing."""
    left_price = parse_price(left)
    right_price = parse_price(right)
    if left_price is None or right_price is None:
        return "-"
    diff_ratio = abs(left_price - right_price) / max(left_price, right_price)
    return f"{diff_ratio * 100:.1f}%"


def price_context(inventory_price, candidate_price) -> str:
    """Build AI prompt context for price as a tie-breaker only."""
    return (
        f"inventory={format_price(inventory_price)}, "
        f"candidate={format_price(candidate_price)}, "
        f"delta={price_delta_text(inventory_price, candidate_price)}"
    )
