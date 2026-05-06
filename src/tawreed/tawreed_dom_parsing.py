"""Fallback DOM-scraping logic for Tawreed product rows."""

from __future__ import annotations

import re
from typing import Any

from .tawreed_constants import MAX_DOM_SEARCH_ROWS
from .tawreed_dom_fields import (
    FAST_OPTIONAL_TEXT_TIMEOUT_MS,
    _badge_int,
    _dom_candidate,
    _inner_text,
    _normalize_ocr_zero,
)
from .tawreed_ui import is_no_results_row, visible_product_rows

_NUMERIC_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?")


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
    q_nums = _NUMERIC_TOKEN_RE.findall(_normalize_ocr_zero(query))
    if not q_nums:
        return True
    r_nums = _NUMERIC_TOKEN_RE.findall(arabic_name)
    return bool(set(q_nums) & set(r_nums))
