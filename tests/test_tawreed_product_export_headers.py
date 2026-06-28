"""Tests for Tawreed product export request capture helpers."""

from __future__ import annotations

import unittest
from typing import Any

from src.tawreed.tawreed_product_export import capture_product_search_request


class TawreedProductExportHeaderTests(unittest.TestCase):
    """Validate captured Tawreed product-search request metadata."""

    def test_capture_product_search_request_uses_observed_body(self) -> None:
        page = _FakeCapturePage({"mode": "error", "data": {"productName": "A"}})

        request = capture_product_search_request(page, "A")

        self.assertEqual(request.term, "A")
        self.assertEqual(request.body, {"mode": "error", "data": {"productName": "A"}})
        self.assertEqual(request.headers, {"x-token": "abc", "Authorization": "Bearer t"})
        self.assertEqual(page.search.actions, ["click", "fill:", "fill:A", "press:Enter"])

    def test_capture_product_search_request_waits_for_matching_term(self) -> None:
        page = _FakeCapturePage(
            {"mode": "error", "data": {"displayType": 1}},
            {"mode": "error", "data": {"productName": "ابيمول", "displayType": 1}},
        )

        request = capture_product_search_request(page, "ابيمول")

        self.assertEqual(request.body["data"]["productName"], "ابيمول")


class _FakeCapturePage:
    def __init__(self, *bodies: dict[str, Any]) -> None:
        self.search = _FakeSearch()
        self.responses = [_FakeResponse(body) for body in bodies]

    def expect_response(self, pattern: Any, timeout: int) -> "_FakeResponseContext":
        matching_response = next(
            response for response in self.responses if pattern(response)
        )
        return _FakeResponseContext(matching_response)

    def locator(self, selector: str) -> "_FakeLocator":
        return _FakeLocator(self.search)


class _FakeResponseContext:
    def __init__(self, response: "_FakeResponse") -> None:
        self.value = response

    def __enter__(self) -> "_FakeResponseContext":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


class _FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self.url = "https://api.tawreed.io/rest/v2/stores/products/search/similar5"
        self.request = _FakeRequest(body)


class _FakeRequest:
    headers = {"x-token": "abc", "Authorization": "Bearer t", "content-type": "json"}

    def __init__(self, body: dict[str, Any]) -> None:
        self.post_data_json = body


class _FakeLocator:
    def __init__(self, search: "_FakeSearch") -> None:
        self.first = search


class _FakeSearch:
    def __init__(self) -> None:
        self.actions: list[str] = []

    def click(self) -> None:
        self.actions.append("click")

    def fill(self, value: str) -> None:
        self.actions.append(f"fill:{value}")

    def press(self, key: str) -> None:
        self.actions.append(f"press:{key}")


if __name__ == "__main__":
    unittest.main()
