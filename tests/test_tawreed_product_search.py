"""Tests for Tawreed product-search API helpers."""

from __future__ import annotations

import unittest

from src.tawreed.tawreed_product_search import _api_candidates, _search_response_pattern


class TawreedProductSearchTests(unittest.TestCase):
    """Validate API-first product-search helpers."""

    def test_api_candidates_returns_search_payload_data(self) -> None:
        """Search payload data is used as the product candidate source."""
        payload = {
            "data": [
                {
                    "productId": 16611,
                    "productName": "فيتاسيد سي 1 جم 12 اقراص فوار",
                    "productNameEn": "VITACID C 1 GM 12 EFF. TAB.",
                }
            ]
        }

        candidates = _api_candidates(payload)

        self.assertEqual(candidates[0]["productNameEn"], "VITACID C 1 GM 12 EFF. TAB.")

    def test_search_response_pattern_matches_tawreed_search_endpoint(self) -> None:
        """Search response matcher targets the Tawreed product-search endpoint."""
        pattern = _search_response_pattern()

        self.assertIsNotNone(
            pattern.search("https://seller.tawreed.io/stores/products/search/similar5")
        )


if __name__ == "__main__":
    unittest.main()
