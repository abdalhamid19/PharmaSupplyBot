"""Header capture helpers for Tawreed product catalog exports."""

from __future__ import annotations

from playwright.sync_api import Page

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


def _submit_blank_search(page: Page) -> None:
    search = page.locator(PRODUCT_SEARCH_INPUT_SELECTOR).first
    search.click()
    search.fill("")
    search.press("Enter")


def _reusable_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() == "authorization" or key.lower().startswith("x-")
    }
