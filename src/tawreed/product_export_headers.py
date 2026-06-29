"""Tawreed product export header capture helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page, Response

from .product_export_searches import ProductSearchRequest
from .tawreed_product_search import (
    PRODUCT_SEARCH_INPUT_SELECTOR,
    _search_response_pattern,
)


def capture_product_search_headers(page: Page) -> dict[str, str]:
    """Return reusable Tawreed product-search headers from a browser request."""
    try:
        with page.expect_response(_search_response_pattern(), timeout=5000) as response:
            _submit_blank_search(page)
        return _reusable_headers(response.value.request.headers)
    except Exception:
        return {}


def capture_product_search_request(page: Page, term: str) -> ProductSearchRequest:
    """Return reusable Tawreed product-search metadata for one search term."""
    try:
        with page.expect_response(
            lambda response: _is_expected_search_response(response, term),
            timeout=5000,
        ) as response:
            _submit_search(page, term)
        request = response.value.request
        return ProductSearchRequest(
            term=term,
            headers=_reusable_headers(request.headers),
            body=_request_body(request),
        )
    except Exception as error:
        raise RuntimeError(_capture_error_message(term)) from error


def _submit_blank_search(page: Page) -> None:
    _submit_search(page, "")


def _submit_search(page: Page, term: str) -> None:
    search = page.locator(PRODUCT_SEARCH_INPUT_SELECTOR).first
    search.click()
    search.fill("")
    if term:
        search.fill(term)
    search.press("Enter")


def _request_body(request: Any) -> dict[str, Any]:
    try:
        body = request.post_data_json
    except Exception:
        body = json.loads(request.post_data or "{}")
    if isinstance(body, dict):
        return body
    raise RuntimeError("Captured Tawreed product-search request body is not an object")


def _is_expected_search_response(response: Response, term: str) -> bool:
    if not _search_response_pattern().search(response.url):
        return False
    return _search_body_term(_request_body(response.request)) == term


def _search_body_term(body: dict[str, Any]) -> str:
    data = body.get("data")
    if not isinstance(data, dict):
        return ""
    return str(data.get("productName") or "").strip()


def _capture_error_message(term: str) -> str:
    label = "general export search" if not term else f"export search '{term}'"
    return f"Could not capture Tawreed product-search request for {label}"


def _reusable_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() == "authorization" or key.lower().startswith("x-")
    }


__all__ = [
    "capture_product_search_headers",
    "capture_product_search_request",
]
