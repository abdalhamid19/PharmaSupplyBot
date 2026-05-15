"""Tests for Tawreed API execution-mode defaults and discovery."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.tawreed.tawreed_api import TawreedApiClient
from src.tawreed.tawreed_api_discovery import save_api_contract_capture


class TawreedApiExecutionModeTests(unittest.TestCase):
    """Validate strict API search defaults and browser-discovered contracts."""

    def test_missing_contract_still_has_default_product_search(self) -> None:
        """Strict API match-only can use the known read-only search endpoint."""
        with TemporaryDirectory() as temp_dir:
            client = _CapturingClient(
                "https://seller.tawreed.io/#/login",
                Path(temp_dir) / "state.json",
                Path(temp_dir) / "missing.json",
            )
            rows = client.search_products("BEBELAC AR MILK")

        self.assertEqual(rows[0]["storeProductId"], "s1")
        self.assertIn("stores/products/search/similar5", client.last_url)
        self.assertEqual(client.last_body["data"]["globalSearch"], "BEBELAC AR MILK")
        self.assertTrue(client.contract_field_available("product_search_url"))

    def test_discovery_merges_browser_captured_endpoints(self) -> None:
        """Captured browser requests add endpoints without dropping existing ones."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "contract.json"
            path.write_text(
                json.dumps({"add_to_cart_url": "https://api.test/cart/add"}),
                encoding="utf-8",
            )
            save_api_contract_capture(
                [
                    {
                        "url": "https://api.test/rest/v2/stores/products/search/similar5",
                        "body": {"data": {"displayType": 1}},
                    },
                    {"url": "https://api.test/cart/remove", "body": {"data": {}}},
                ],
                path,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertIn("similar5", payload["product_search_url"])
        self.assertIn("cart/add", payload["add_to_cart_url"])
        self.assertIn("cart/remove", payload["remove_cart_url"])


class _CapturingClient(TawreedApiClient):
    last_url = ""
    last_body = {}

    def _post_json(self, url, body):
        self.last_url = url
        self.last_body = body
        return {"data": [{"productName": "BEBELAC", "storeProductId": "s1"}]}


if __name__ == "__main__":
    unittest.main()
