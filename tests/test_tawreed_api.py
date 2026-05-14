"""Tests for optional Tawreed API execution support."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.tawreed.tawreed_api import (
    TawreedApiClient,
    TawreedApiUnavailable,
)
from src.tawreed.tawreed_api_contract import (
    load_api_contract,
    save_discovered_api_contract,
)


class TawreedApiTests(unittest.TestCase):
    """Validate local API contract parsing and safe unavailable behavior."""

    def test_load_missing_contract_disables_mutating_api(self) -> None:
        with TemporaryDirectory() as temp_dir:
            client = TawreedApiClient(
                "https://seller.tawreed.io/#/login",
                Path(temp_dir) / "wardany.json",
                Path(temp_dir) / "missing.json",
            )

        with self.assertRaises(TawreedApiUnavailable):
            client.add_to_cart(object(), 1)

    def test_save_discovered_contract_selects_known_endpoint_types(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "contract.json"
            contract = save_discovered_api_contract(
                [
                    {"url": "https://api.tawreed.io/rest/v2/cart/add", "body": {"data": {}}},
                    {
                        "url": "https://api.tawreed.io/rest/v2/product-search",
                        "body": {"data": {"displayType": 1}},
                    },
                ],
                output,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn("product-search", contract.product_search_url)
        self.assertIn("cart/add", payload["add_to_cart_url"])

    def test_load_api_contract_round_trips_saved_json(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "contract.json"
            path.write_text(
                json.dumps({"product_search_url": "/rest/v2/product-search"}),
                encoding="utf-8",
            )

            contract = load_api_contract(path)

        self.assertEqual(contract.product_search_url, "/rest/v2/product-search")


if __name__ == "__main__":
    unittest.main()
