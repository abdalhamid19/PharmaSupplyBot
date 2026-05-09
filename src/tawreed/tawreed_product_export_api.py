"""API pagination helpers for exporting Tawreed store products."""

from __future__ import annotations

from typing import Any, Iterator

from playwright.sync_api import Page

from .tawreed_constants import PRODUCT_SEARCH_ENDPOINT
from .tawreed_product_search import _api_candidates

DEFAULT_EXPORT_PAGE_SIZE = 100
DEFAULT_EXPORT_STEM = "tawreed_products"
EXPORT_REQUEST_BODY = {"mode": "error", "langCode": "ar", "data": {"displayType": 1}}


def iter_all_product_candidates(
    page: Page,
    page_size: int = DEFAULT_EXPORT_PAGE_SIZE,
    limit: int = 0,
    headers: dict[str, str] | None = None,
    request_body: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield Tawreed product candidates from every products API page."""
    emitted = 0
    for payload in _iter_product_page_payloads(
        page, page_size, headers or {}, request_body
    ):
        candidates = _api_candidates(payload)
        if not candidates:
            break
        for candidate in candidates:
            yield candidate
            emitted += 1
            if limit and emitted >= limit:
                return


def _iter_product_page_payloads(
    page: Page,
    page_size: int,
    headers: dict[str, str],
    request_body: dict[str, Any] | None,
) -> Iterator[dict[str, Any]]:
    total_pages, page_number = None, 0
    while total_pages is None or page_number < total_pages:
        payload = _fetch_products_page(
            page, page_number, page_size, headers, request_body
        )
        total_pages = _total_pages_from_payload(payload)
        yield payload
        page_number += 1


def product_export_url(page: Page, page_number: int, page_size: int) -> str:
    """Return the absolute Tawreed product-search API URL for one page."""
    origin = _api_origin(page)
    return (
        f"{origin}/rest/v2/{PRODUCT_SEARCH_ENDPOINT}"
        f"?sort=productName,asc&page={page_number}&size={page_size}"
    )


def _total_pages_from_payload(payload: dict[str, Any]) -> int:
    total_pages = int(_payload_page_data(payload).get("totalPages") or 1)
    return max(total_pages, 1)


def _fetch_products_page(
    page: Page,
    page_number: int,
    page_size: int,
    headers: dict[str, str],
    request_body: dict[str, Any] | None,
) -> dict[str, Any]:
    response = page.request.post(
        product_export_url(page, page_number, page_size),
        data=request_body or EXPORT_REQUEST_BODY,
        headers=headers,
    )
    if not response.ok:
        raise RuntimeError(
            f"Tawreed products export API returned HTTP {response.status}"
        )
    return response.json()


def _payload_page_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def _api_origin(page: Page) -> str:
    origin = page.evaluate("() => location.origin")
    if "seller.tawreed.io" in str(origin):
        return "https://api.tawreed.io"
    return str(origin).rstrip("/")
