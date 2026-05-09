"""Search term helpers for Tawreed product catalog exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from playwright.sync_api import Page

from .tawreed_product_export_api import (
    DEFAULT_EXPORT_PAGE_SIZE,
    iter_all_product_candidates,
)

ENGLISH_EXPORT_SEARCH_TERMS = tuple(
    chr(code) for code in range(ord("A"), ord("Z") + 1)
)
ARABIC_EXPORT_SEARCH_TERMS = (
    "ا", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر", "ز", "س", "ش",
    "ص", "ض", "ط", "ظ", "ع", "غ", "ف", "ق", "ك", "ل", "م", "ن", "ه",
    "و", "ي",
)
EXPORT_SEARCH_TERMS = ("",) + ENGLISH_EXPORT_SEARCH_TERMS + ARABIC_EXPORT_SEARCH_TERMS


@dataclass(frozen=True)
class ProductSearchRequest:
    """Reusable Tawreed product-search request metadata for one query."""

    term: str
    headers: dict[str, str]
    body: dict[str, Any]


def iter_product_search_candidates(
    page: Page,
    search_requests: Iterator[ProductSearchRequest],
    page_size: int = DEFAULT_EXPORT_PAGE_SIZE,
    limit: int = 0,
) -> Iterator[dict[str, Any]]:
    """Yield product candidates for captured search requests in input order."""
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
