"""Pricing and discount parsing logic for Tawreed API payloads."""

from __future__ import annotations
import re
from typing import Any
from ..tawreed_constants import DISCOUNT_KEYS, NESTED_STORE_KEYS

_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")

def first_discount_value(source: dict[str, Any]) -> Any:
    """Return the first discount value found in a Tawreed payload."""
    for key in DISCOUNT_KEYS:
        val = source.get(key)
        if isinstance(val, dict):
            nest = first_discount_value(val)
            if nest not in (None, ""): return nest
            continue
        if val not in (None, ""): return val
    
    for o_key in NESTED_STORE_KEYS:
        nest = source.get(o_key)
        if isinstance(nest, dict):
            nest_val = first_discount_value(nest)
            if nest_val not in (None, ""): return nest_val
    
    return _calculate_discount_from_prices(source)


def _calculate_discount_from_prices(source):
    """Calculate discount from sale and public prices."""
    try:
        sale_price = float(str(source.get("salePrice") or "0").replace(",", ""))
        price_keys = ["retailPrice", "publicPrice", "price", "sellingPrice"]
        pub_price = float(str(next((source.get(k) for k in price_keys if source.get(k)), "0")).replace(",", ""))
        if pub_price > 0 and sale_price > 0 and sale_price < pub_price:
            return round(((pub_price - sale_price) / pub_price) * 100, 2)
    except Exception:
        pass
    return ""

def format_discount_percent(value: Any) -> str:
    """Format Tawreed discount values consistently for output."""
    if value in (None, ""): return ""
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped: return ""
        match = _NUMBER_RE.search(stripped)
        if not match: return stripped
        num = float(match.group(0).replace(",", "."))
        if "%" in stripped or "٪" in stripped:
            return f"{num:g}%"
        return _format_discount_number(num)
    try:
        return _format_discount_number(float(value))
    except Exception:
        return str(value).strip()

def discount_value_as_percent(value: Any) -> float:
    """Return a numeric percent value for sorting discounts."""
    if value in (None, ""): return -1.0
    if isinstance(value, str):
        match = _NUMBER_RE.search(value.strip())
        if not match: return -1.0
        value = float(match.group(0).replace(",", "."))
    try:
        num = float(value)
    except Exception: return -1.0
    return num * 100 if 0 < num < 1 else num

def _format_discount_number(value: float) -> str:
    """Return a percent string, treating fractional values as rates."""
    percent = value * 100 if 0 < value < 1 else value
    return f"{percent:g}%"
