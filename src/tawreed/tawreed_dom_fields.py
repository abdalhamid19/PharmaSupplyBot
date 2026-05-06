"""Low-level DOM field parsing helpers for Tawreed product rows."""

from __future__ import annotations

import re
from typing import Any

_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_NUMERIC_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?")
_OCR_ZERO_RE = re.compile(r"(?<=\d)[Oo](?=\b|[^A-Za-z0-9])")
_WHITESPACE_RE = re.compile(r"\s+")
FAST_OPTIONAL_TEXT_TIMEOUT_MS = 300


def _dom_candidate(
    lines, query: str, s_count: int, c_count: int, row
) -> dict[str, Any]:
    return {
        "productNameEn": _fallback_english_name(query, lines[0]),
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


def _fallback_english_name(query: str, arabic_name: str) -> str:
    normalized_query = _normalize_ocr_zero(query.strip())
    q_tokens = [t for t in _WHITESPACE_RE.split(normalized_query) if t]
    non_num = [t for t in q_tokens if not any(ch.isdigit() for ch in t)]
    ar_num = _NUMERIC_TOKEN_RE.findall(arabic_name)
    return " ".join(non_num + ar_num) or normalized_query


def _normalize_ocr_zero(text: str) -> str:
    return _OCR_ZERO_RE.sub("0", text)


def _row_unavailable_message(row) -> str:
    try:
        return _inner_text(row.locator("div[style*='color: red']").first, 300).strip()
    except Exception:
        return ""


class _SuppressAll:
    def __enter__(self):
        pass

    def __exit__(self, t, v, tb):
        return True
