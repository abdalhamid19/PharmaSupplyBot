"""Tests for Tawreed API execution-mode defaults and discovery."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.tawreed.tawreed_api import TawreedApiClient
from src.tawreed.tawreed_api_discovery import save_api_contract_capture
from src.tawreed.tawreed_api_flow import match_items_only_with_api
from src.tawreed.tawreed_api_matching import require_api_match
from src.tawreed.tawreed_api_matching import _has_only_non_orderable_candidates
from src.core.matching_models import MatchDecision, SearchMatch
from src.core.utils.excel import Item


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
        self.assertEqual(client.last_body["data"]["productName"], "BEBELAC AR MILK")
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

    def test_detects_api_candidates_without_orderable_ids(self) -> None:
        """API results without storeProductId should report a clearer skip reason."""
        results = [
            ("LEVIASILLS", [{"productNameEn": "LEVIASILLS LOZENGES ORANGE"}])
        ]

        self.assertTrue(_has_only_non_orderable_candidates(results))
        self.assertFalse(
            _has_only_non_orderable_candidates(
                [("KENACOMB", [{"storeProductId": "1460790"}])]
            )
        )

    def test_api_match_only_flow_reuses_one_client_for_all_items(self) -> None:
        """One API flow should use one long-lived API client across item searches."""
        clients: list[_FakeFlowClient] = []

        def build_client(*_args, **_kwargs):
            client = _FakeFlowClient()
            clients.append(client)
            return client

        def require_match(_bot, api, item, _require_available):
            api.search_products(item.name)
            return SimpleNamespace(query=item.name)

        bot = _FlowBot()
        items = [Item("1", "PANADOL", 1), Item("2", "CATAFLAM", 1)]
        with (
            patch("src.tawreed.tawreed_api_flow.TawreedApiClient", side_effect=build_client),
            patch("src.tawreed.tawreed_api_flow.require_api_match", side_effect=require_match),
        ):
            match_items_only_with_api(bot, items)

        self.assertEqual(len(clients), 1)
        self.assertEqual(clients[0].entered, 1)
        self.assertEqual(clients[0].closed, 1)
        self.assertEqual(clients[0].queries, ["PANADOL", "CATAFLAM"])
        self.assertEqual(bot.successes, 2)

    def test_saved_manual_review_api_match_records_elapsed_time(self) -> None:
        bot = _ApiMatchBot()
        item = Item("1", "PANADOL", 1)
        candidate = {"productNameEn": "PANADOL", "storeProductId": "s1"}
        decision = MatchDecision(
            SearchMatch("PANADOL", 0, 999.0, candidate),
            [],
            "Approved by saved manual review (ID match).",
        )
        with (
            patch("src.tawreed.tawreed_api_matching.manual_review_queries", return_value=["PANADOL"]),
            patch("src.tawreed.tawreed_api_matching.saved_manual_review_decision", return_value=object()),
            patch("src.tawreed.tawreed_api_matching.manual_review_match", return_value=decision),
        ):
            match = require_api_match(bot, _ApiSearchClient(candidate), item, False)

        self.assertEqual(match.data["storeProductId"], "s1")
        self.assertGreater(bot.last_match_elapsed_seconds, 0)


class _CapturingClient(TawreedApiClient):
    last_url = ""
    last_body = {}

    def _post_json(self, url, body):
        self.last_url = url
        self.last_body = body
        return {"data": [{"productName": "BEBELAC", "storeProductId": "s1"}]}


class _FakeFlowClient:
    def __init__(self) -> None:
        self.entered = 0
        self.closed = 0
        self.queries: list[str] = []

    def __enter__(self):
        self.entered += 1
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.closed += 1

    def contract_field_available(self, field: str) -> bool:
        return field == "product_search_url"

    def warm_up(self) -> None:
        pass

    def search_products(self, query: str):
        self.queries.append(query)
        return [{"productNameEn": query, "storeProductId": "s1"}]


class _FlowBot:
    profile_key = "wardany"
    config = SimpleNamespace(base_url="https://seller.tawreed.io/#/login")
    state_path = Path("state/wardany.json")
    skip_item_exception = RuntimeError

    def __init__(self) -> None:
        self.successes = 0

    def _stop_before_item(self, item) -> bool:
        return False

    def _reset_last_item_state(self) -> None:
        pass

    def log(self, message: str) -> None:
        pass

    def _record_match_only_success(self, item, started_at) -> None:
        self.successes += 1

    def _record_match_only_skip(self, item, error, started_at) -> None:
        raise error


class _ApiMatchBot:
    config = SimpleNamespace(matching=SimpleNamespace())
    skip_item_exception = RuntimeError

    def __init__(self) -> None:
        self.last_match_elapsed_seconds = 0.0
        self.last_match_decision = None
        self.last_searched_queries = []
        self.last_item_timings = {}


class _ApiSearchClient:
    def __init__(self, candidate: dict) -> None:
        self.candidate = candidate

    def search_products(self, query: str):
        return [self.candidate]


if __name__ == "__main__":
    unittest.main()
