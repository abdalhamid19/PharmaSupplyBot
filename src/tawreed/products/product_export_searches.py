"""Tawreed product export search term helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Constants
ENGLISH_EXPORT_SEARCH_TERMS = tuple(
    chr(code) for code in range(ord("A"), ord("Z") + 1)
)
ARABIC_EXPORT_SEARCH_TERMS = (
    "ا", "أ", "إ", "آ", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر",
    "ز", "س", "ش", "ص", "ض", "ط", "ظ", "ع", "غ", "ف", "ق", "ك", "ل",
    "م", "ن", "ه", "ة", "و", "ي", "ى",
)
EXPORT_SEARCH_TERMS = ("",) + ENGLISH_EXPORT_SEARCH_TERMS + ARABIC_EXPORT_SEARCH_TERMS
EXPORT_SEARCH_GROUPS = (
    ("general catalog pages", ("",)),
    ("English alphabet searches", ENGLISH_EXPORT_SEARCH_TERMS),
    ("Arabic alphabet searches", ARABIC_EXPORT_SEARCH_TERMS),
)


@dataclass(frozen=True)
class ProductSearchRequest:
    """Reusable Tawreed product-search request metadata for one query."""

    term: str
    headers: dict[str, str]
    body: dict[str, Any]


def iter_product_search_candidates(
    page,
    search_requests,
    page_size: int = 100,
    limit: int = 0,
):
    """Yield product candidates for captured search requests in input order."""
    from .product_export_api import iter_all_product_candidates

    emitted = 0
    for search_request in search_requests:
        candidates = iter_all_product_candidates(
            page, page_size, 0, search_request.headers, search_request.body
        )
        for candidate in candidates:
            yield candidate
            emitted += 1
            if limit and emitted >= limit:
                return


__all__ = [
    "ENGLISH_EXPORT_SEARCH_TERMS",
    "ARABIC_EXPORT_SEARCH_TERMS",
    "EXPORT_SEARCH_TERMS",
    "EXPORT_SEARCH_GROUPS",
    "ProductSearchRequest",
    "iter_product_search_candidates",
]
