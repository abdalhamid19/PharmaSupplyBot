"""DOM parsing and fallback helpers for Tawreed product rows - unified module."""

from __future__ import annotations

import re
from typing import Any

from .tawreed_constants import MAX_DOM_SEARCH_ROWS
from .tawreed_ui import is_no_results_row, visible_product_rows

_NUMERIC_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?")
_OCR_ZERO_RE = re.compile(r"(?<=\d)[Oo](?=\b|[^A-Za-z0-9])")
_WHITESPACE_RE = re.compile(r"\s+")
_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
FAST_OPTIONAL_TEXT_TIMEOUT_MS = 300


# ============================================================================
# Fallback English names (from tawreed_dom_fallback.py)
# ============================================================================

def fallback_english_name(query: str, arabic_name: str) -> str:
    """Return a synthetic English name using query words and DOM row numbers."""
    normalized_query = normalize_fallback_query(query)
    q_tokens = [t for t in _WHITESPACE_RE.split(normalized_query) if t]
    query_numbers = _NUMERIC_TOKEN_RE.findall(normalized_query)
    row_numbers = _NUMERIC_TOKEN_RE.findall(arabic_name)
    if query_numbers and set(query_numbers).issubset(set(row_numbers)):
        return normalized_query
    non_num = [t for t in q_tokens if not any(ch.isdigit() for ch in t)]
    return " ".join(non_num + row_numbers) or normalized_query


def normalize_fallback_query(query: str) -> str:
    """Normalize OCR zeros and compact numeric tokens for DOM plausibility checks."""
    text = _OCR_ZERO_RE.sub("0", query.strip())
    text = re.sub(r"([A-Za-z])(?=\d)", r"\1 ", text)
    text = re.sub(r"(?<=\d)([A-Za-z])", r" \1", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


# ============================================================================
# DOM field parsing (from tawreed_dom_fields.py)
# ============================================================================

def _dom_candidate(
    lines, query: str, s_count: int, c_count: int, row
) -> dict[str, Any]:
    return {
        "productNameEn": "",
        "productNameEnFallback": fallback_english_name(query, lines[0]),
        "productNameEnSynthetic": True,
        "productName": lines[0],
        "productsCount": s_count,
        "availableQuantity": _dom_available_qty(row, s_count, c_count),
        "discountPercent": _row_discount_percent(row),
        "supplierName": _row_supplier_name(lines),
        "storeProductId": f"dom-row-{_normalized_dom_id(lines[0])}",
    }


def _badge_int(row, selector: str) -> int:
    try:
        text = _inner_text(row.locator(selector).first, FAST_OPTIONAL_TEXT_TIMEOUT_MS)
        return int(float(text.strip()))
    except Exception:
        return 0


def _dom_available_qty(row, s_count: int, c_count: int) -> int:
    if _row_unavailable_message(row):
        return 0
    return max(c_count, s_count) if (s_count > 0 or c_count > 0) else 0


def _row_discount_percent(row) -> str:
    with _SuppressAll():
        green = row.locator("td").nth(1).locator(".text-green-500").first
        return _inner_text(green, 300).strip()
    with _SuppressAll():
        return _first_number(_inner_text(row.locator("td").nth(1), 300))
    return ""


def _row_supplier_name(lines: list[str]) -> str:
    if len(lines) < 2:
        return ""
    supplier = lines[1].strip()
    return "" if "غير متوفر" in supplier else supplier


def _inner_text(locator, timeout_ms: int) -> str:
    try:
        return str(locator.inner_text(timeout=timeout_ms))
    except Exception:
        return ""


def _first_number(text: str) -> str:
    match = _NUMBER_RE.search(str(text or ""))
    return match.group(0).replace(",", ".") if match else ""


def _normalized_dom_id(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text)[:48]


def _row_unavailable_message(row) -> str:
    try:
        return _inner_text(row.locator("div[style*='color: red']").first, 300).strip()
    except Exception:
        return ""


class _SuppressAll:
    def __enter__(self): pass

    def __exit__(self, t, v, tb): return True


# ============================================================================
# DOM search results (from tawreed_dom_parsing.py)
# ============================================================================

def dom_search_results(page, query: str) -> list[dict[str, Any]]:
    """Build fallback product candidates from the visible products table rows."""
    results: list[dict[str, Any]] = []
    rows = visible_product_rows(page)
    for i in range(min(rows.count(), MAX_DOM_SEARCH_ROWS)):
        row = rows.nth(i)
        if is_no_results_row(row):
            continue
        candidate = _dom_candidate_from_row(row, query)
        if candidate:
            results.append(candidate)
    return results


def _dom_candidate_from_row(row, query: str) -> dict[str, Any] | None:
    """Return one fallback candidate parsed from a rendered products-table row."""
    lines = _row_name_lines(row)
    if not lines or not _row_is_plausible(lines[0], query):
        return None
    s_count = _badge_int(row, "button:has(.pi-building) .p-badge")
    c_count = _badge_int(row, "button:has(.pi-shopping-cart) .p-badge")
    return _dom_candidate(lines, query, s_count, c_count, row)


def _row_name_lines(row) -> list[str]:
    """Return the visible product-name block lines for one rendered row."""
    try:
        div = row.locator("td").first.locator("div.flex.flex-column").first
        text = _inner_text(div, FAST_OPTIONAL_TEXT_TIMEOUT_MS).strip()
        return [line.strip() for line in text.splitlines() if line.strip()]
    except Exception:
        return []


def _row_is_plausible(arabic_name: str, query: str) -> bool:
    """Return whether a DOM row is numerically plausible for the query."""
    q_nums = _NUMERIC_TOKEN_RE.findall(normalize_fallback_query(query))
    if not q_nums:
        return True
    r_nums = _NUMERIC_TOKEN_RE.findall(arabic_name)
    return bool(set(q_nums) & set(r_nums))


__all__ = [
    # Fallback names
    "fallback_english_name",
    "normalize_fallback_query",
    # DOM parsing
    "dom_search_results",
    "FAST_OPTIONAL_TEXT_TIMEOUT_MS",
    # Internal helpers
    "_row_name_lines",
]
