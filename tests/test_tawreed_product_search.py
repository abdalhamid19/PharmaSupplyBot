"""Tests for Tawreed product-search API helpers."""

from __future__ import annotations

import unittest

from src.tawreed.tawreed_product_search import (
    _api_candidates,
    _search_response_pattern,
)
from src.tawreed.tawreed_product_search_select import select_search_candidates


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

    def test_api_candidates_handles_nested_payload_data(self) -> None:
        """Nested search payload data is flattened to product candidates."""
        payload = {
            "data": {
                "content": [
                    {
                        "productName": "فيتاسيد سي 1 جم 12 اقراص فوار",
                        "productNameEn": "VITACID C 1 GM 12 EFF. TAB.",
                    }
                ]
            }
        }

        candidates = _api_candidates(payload)

        self.assertEqual(candidates[0]["productNameEn"], "VITACID C 1 GM 12 EFF. TAB.")

    def test_search_response_pattern_matches_tawreed_search_endpoint(self) -> None:
        """Search response matcher targets the Tawreed product-search endpoint."""
        pattern = _search_response_pattern()

        self.assertIsNotNone(
            pattern.search("https://seller.tawreed.io/stores/products/search/similar5")
        )

    def test_dom_candidates_replace_api_rows_without_orderable_ids(self) -> None:
        """API rows without store ids are partial data and should use DOM fallback."""
        api_rows = [{"productNameEn": "PANADOL"}]
        dom_rows = [{"productNameEn": "PANADOL", "storeProductId": "dom-row-panadol"}]

        selected = select_search_candidates(api_rows, dom_rows)

        self.assertEqual(selected, dom_rows)

    def test_orderable_api_candidates_remain_preferred(self) -> None:
        """API rows with store ids remain the preferred source."""
        api_rows = [{"productNameEn": "PANADOL", "storeProductId": "s1"}]
        dom_rows = [{"productNameEn": "PANADOL", "storeProductId": "dom-row-panadol"}]

        selected = select_search_candidates(api_rows, dom_rows)

        self.assertEqual(selected, api_rows)


if __name__ == "__main__":
    unittest.main()
