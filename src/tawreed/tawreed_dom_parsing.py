"""Fallback DOM-scraping logic for Tawreed product rows."""

from __future__ import annotations
import re
from typing import Any
from .tawreed_ui import cart_button, visible_product_rows, is_no_results_row
from .tawreed_constants import MAX_DOM_SEARCH_ROWS

_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_NUMERIC_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?")
_WHITESPACE_RE = re.compile(r"\s+")
FAST_OPTIONAL_TEXT_TIMEOUT_MS = 300

def dom_search_results(page, query: str) -> list[dict[str, Any]]:
    """Build fallback product candidates from the visible products table rows."""
    results: list[dict[str, Any]] = []
    rows = visible_product_rows(page)
    for i in range(min(rows.count(), MAX_DOM_SEARCH_ROWS)):
        row = rows.nth(i)
        if is_no_results_row(row): continue
        candidate = _dom_candidate_from_row(row, query)
        if candidate: results.append(candidate)
    return results

def _dom_candidate_from_row(row, query: str) -> dict[str, Any] | None:
    """Return one fallback candidate parsed from a rendered products-table row."""
    lines = _row_name_lines(row)
    if not lines or not _row_is_plausible(lines[0], query): return None
    s_count = _badge_int(row, "button:has(.pi-building) .p-badge")
    c_count = _badge_int(row, "button:has(.pi-shopping-cart) .p-badge")
    return {
        "productNameEn": _fallback_english_name(query, lines[0]),
        "productName": lines[0],
        "productsCount": s_count,
        "availableQuantity": _dom_available_qty(row, s_count, c_count),
        "discountPercent": _row_discount_percent(row),
        "supplierName": _row_supplier_name(lines),
        "storeProductId": f"dom-row-{_normalized_dom_id(lines[0])}",
    }

def _row_name_lines(row) -> list[str]:
    """Return the visible product-name block lines for one rendered row."""
    try:
        div = row.locator("td").first.locator("div.flex.flex-column").first
        text = _inner_text(div, FAST_OPTIONAL_TEXT_TIMEOUT_MS).strip()
        return [L.strip() for L in text.splitlines() if L.strip()]
    except Exception: return []

def _badge_int(row, selector: str) -> int:
    """Return an integer badge value from the row or zero when absent."""
    try:
        text = _inner_text(row.locator(selector).first, FAST_OPTIONAL_TEXT_TIMEOUT_MS).strip()
        return int(float(text))
    except Exception: return 0

def _dom_available_qty(row, s_count: int, c_count: int) -> int:
    """Return visible DOM availability."""
    if _row_unavailable_message(row): return 0
    return max(c_count, s_count) if (s_count > 0 or c_count > 0) else 0

def _row_discount_percent(row) -> str:
    """Return the visible discount percent from one products-table row."""
    with suppress_all():
        return _inner_text(row.locator("td").nth(1).locator(".text-green-500").first, 300).strip()
    with suppress_all():
        return _first_number(_inner_text(row.locator("td").nth(1), 300))
    return ""

def _row_supplier_name(lines: list[str]) -> str:
    """Return the visible supplier/store line from one products-table row."""
    if len(lines) < 2: return ""
    supplier = lines[1].strip()
    return "" if "غير متوفر" in supplier else supplier

def _inner_text(locator, timeout_ms: int) -> str:
    """Read locator text with a short timeout."""
    try: return str(locator.inner_text(timeout=timeout_ms))
    except Exception: return ""

def _first_number(text: str) -> str:
    """Return the first decimal-like number from visible row text."""
    match = _NUMBER_RE.search(str(text or ""))
    return match.group(0).replace(",", ".") if match else ""

def _normalized_dom_id(text: str) -> str:
    """Return a stable ASCII-ish identifier fragment."""
    return "".join(c if c.isalnum() else "-" for c in text)[:48]

def _fallback_english_name(query: str, arabic_name: str) -> str:
    """Return a query-shaped fallback English name."""
    q_tokens = [t for t in _WHITESPACE_RE.split(query.strip()) if t]
    non_num = [t for t in q_tokens if not any(ch.isdigit() for ch in t)]
    ar_num = _NUMERIC_TOKEN_RE.findall(arabic_name)
    return " ".join(non_num + ar_num) or query

def _row_is_plausible(arabic_name: str, query: str) -> bool:
    """Return whether a DOM row is numerically plausible for the query."""
    q_nums = _NUMERIC_TOKEN_RE.findall(query)
    if not q_nums: return True
    r_nums = _NUMERIC_TOKEN_RE.findall(arabic_name)
    return bool(set(q_nums) & set(r_nums))

def _row_unavailable_message(row) -> str:
    """Return the row's visible red status message."""
    try:
        return _inner_text(row.locator("div[style*='color: red']").first, 300).strip()
    except Exception: return ""

class suppress_all:
    """Context manager to suppress all exceptions in DOM scraping fallbacks."""
    def __enter__(self): pass
    def __exit__(self, t, v, tb): return True

