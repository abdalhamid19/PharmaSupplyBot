"""Tests for Tawreed product export API retry helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src.tawreed.tawreed_product_export_retry import post_product_export_json


class TawreedProductExportRetryTests(unittest.TestCase):
    """Validate bounded retries for export API requests."""

    def test_post_product_export_json_retries_timeout_then_succeeds(self) -> None:
        request = _FlakyRequest([TimeoutError("read ETIMEDOUT"), _response("1")])

        with patch("src.tawreed.tawreed_product_export_retry.time.sleep"):
            payload = post_product_export_json(request, "https://api.test", {}, {})

        self.assertEqual(payload["data"]["content"][0]["storeProductId"], "1")
        self.assertEqual(request.calls, 2)
        self.assertEqual(request.timeouts, [60_000, 60_000])

    def test_post_product_export_json_raises_after_bounded_retries(self) -> None:
        request = _FlakyRequest([
            TimeoutError("read ETIMEDOUT"),
            TimeoutError("read ETIMEDOUT"),
            TimeoutError("read ETIMEDOUT"),
        ])

        with patch("src.tawreed.tawreed_product_export_retry.time.sleep"):
            with self.assertRaisesRegex(RuntimeError, "read ETIMEDOUT"):
                post_product_export_json(request, "https://api.test", {}, {})

        self.assertEqual(request.calls, 3)


class _FlakyRequest:
    def __init__(self, results: list[object]) -> None:
        self.results = results
        self.calls = 0
        self.timeouts: list[int] = []

    def post(self, url, data, headers, timeout):
        self.calls += 1
        self.timeouts.append(timeout)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _response(store_product_id: str):
    return _FakeResponse({
        "data": {
            "content": [{"productName": "عربي", "storeProductId": store_product_id}]
        }
    })


class _FakeResponse:
    ok = True
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


if __name__ == "__main__":
    unittest.main()
