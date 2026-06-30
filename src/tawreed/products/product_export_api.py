"""Tawreed product export API helpers with retry logic."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page

# Constants
DEFAULT_EXPORT_PAGE_SIZE = 100
EXPORT_REQUEST_BODY = {"mode": "error", "langCode": "ar", "data": {"displayType": 1}}
EXPORT_API_RETRY_ATTEMPTS = 3
EXPORT_API_TIMEOUT_MS = 60_000
_RETRY_DELAYS_SECONDS = (1.0, 2.0)


def post_product_export_json(
    request_context: Any,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    """POST one product export API request with bounded retries."""
    last_error: Exception | None = None
    for attempt in range(EXPORT_API_RETRY_ATTEMPTS):
        try:
            return _post_once(request_context, url, body, headers)
        except Exception as error:
            last_error = error
            if attempt == EXPORT_API_RETRY_ATTEMPTS - 1:
                break
            time.sleep(_RETRY_DELAYS_SECONDS[attempt])
    raise RuntimeError(f"Tawreed products export API request failed: {last_error}")


def _post_once(
    request_context: Any,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    response = request_context.post(
        url,
        data=body,
        headers=headers,
        timeout=EXPORT_API_TIMEOUT_MS,
    )
    if not response.ok:
        raise RuntimeError(
            f"Tawreed products export API returned HTTP {response.status}"
        )
    return response.json()


def iter_all_product_candidates(
    page: Page,
    page_size: int = DEFAULT_EXPORT_PAGE_SIZE,
    limit: int = 0,
    headers: dict[str, str] | None = None,
    request_body: dict[str, Any] | None = None,
):
    """Yield Tawreed product candidates from every products API page."""
    emitted = 0
    for payload in _iter_product_page_payloads(
        page, page_size, headers or {}, request_body
    ):
        from .tawreed_product_search import _api_candidates
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
):
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
    from ..tawreed_constants import PRODUCT_SEARCH_ENDPOINT
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
    return post_product_export_json(
        page.request,
        product_export_url(page, page_number, page_size),
        request_body or EXPORT_REQUEST_BODY,
        headers,
    )


def _payload_page_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def _api_origin(page: Page) -> str:
    origin = page.evaluate("() => location.origin")
    if "seller.tawreed.io" in str(origin):
        return "https://api.tawreed.io"
    return str(origin).rstrip("/")


__all__ = [
    "DEFAULT_EXPORT_PAGE_SIZE",
    "EXPORT_REQUEST_BODY",
    "EXPORT_API_RETRY_ATTEMPTS",
    "EXPORT_API_TIMEOUT_MS",
    "post_product_export_json",
    "iter_all_product_candidates",
    "product_export_url",
]
