"""Tests for optional Tawreed API execution support."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.tawreed.tawreed_api import (
    TawreedApiClient,
    TawreedApiUnavailable,
    _auth_headers_from_state,
)
from src.tawreed.tawreed_api_contract import (
    load_api_contract,
    save_discovered_api_contract,
)
from src.tawreed.tawreed_api_flow import _submit_order_if_enabled


class _FakeSubmitApi:
    def __init__(self) -> None:
        self.submitted = False

    def submit_order(self) -> None:
        self.submitted = True


class _FakeSubmitBot:
    profile_key = "wardany"

    def __init__(self, submit_order: bool, match_only: bool = False) -> None:
        from types import SimpleNamespace

        self.config = SimpleNamespace(
            runtime=SimpleNamespace(submit_order=submit_order)
        )
        self.match_only = match_only

    def _stop_requested(self) -> bool:
        return False


class _FakeApiResponse:
    ok = True
    status = 200

    def json(self):
        return {"data": [{"productNameEn": "PANADOL", "storeProductId": "s1"}]}


class _FakeRequestContext:
    def __init__(self) -> None:
        self.post_calls = 0
        self.dispose_calls = 0

    def post(self, *args, **kwargs):
        self.post_calls += 1
        return _FakeApiResponse()

    def dispose(self) -> None:
        self.dispose_calls += 1


class _FakeRequestFactory:
    def __init__(self, context: _FakeRequestContext) -> None:
        self.context = context
        self.new_context_calls = 0

    def new_context(self, **kwargs):
        self.new_context_calls += 1
        return self.context


class _FakePlaywright:
    def __init__(self, context: _FakeRequestContext) -> None:
        self.request = _FakeRequestFactory(context)
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


class _FakeSyncPlaywright:
    def __init__(self, playwright: _FakePlaywright) -> None:
        self.playwright = playwright
        self.start_calls = 0

    def start(self):
        self.start_calls += 1
        return self.playwright


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

    def test_api_submit_skips_when_runtime_submit_disabled(self) -> None:
        api = _FakeSubmitApi()

        _submit_order_if_enabled(_FakeSubmitBot(False), api, added_any=True)

        self.assertFalse(api.submitted)

    def test_api_submit_skips_match_only_even_when_submit_enabled(self) -> None:
        api = _FakeSubmitApi()

        _submit_order_if_enabled(
            _FakeSubmitBot(submit_order=True, match_only=True), api, added_any=True
        )

        self.assertFalse(api.submitted)

    def test_api_submit_runs_only_when_all_safety_gates_pass(self) -> None:
        api = _FakeSubmitApi()

        _submit_order_if_enabled(_FakeSubmitBot(True), api, added_any=True)

        self.assertTrue(api.submitted)

    def test_auth_headers_read_access_token_from_storage_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "origins": [
                            {
                                "origin": "https://seller.tawreed.io",
                                "localStorage": [
                                    {"name": "access-token", "value": "abc.def.ghi"}
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            headers = _auth_headers_from_state(state_path)

        self.assertEqual(headers, {"Authorization": "Bearer abc.def.ghi"})

    def test_api_client_reuses_one_request_context_for_multiple_searches(self) -> None:
        context = _FakeRequestContext()
        playwright = _FakePlaywright(context)
        launcher = _FakeSyncPlaywright(playwright)

        with (
            TemporaryDirectory() as temp_dir,
            patch("src.tawreed.tawreed_api.sync_playwright", return_value=launcher),
        ):
            state_path = Path(temp_dir) / "state.json"
            state_path.write_text("{}", encoding="utf-8")
            client = TawreedApiClient(
                "https://seller.tawreed.io/#/login",
                state_path,
                Path(temp_dir) / "missing.json",
            )
            client.warm_up()
            client.search_products("PANADOL")
            client.search_products("PANADOL EXTRA")
            client.close()

        self.assertEqual(launcher.start_calls, 1)
        self.assertEqual(playwright.request.new_context_calls, 1)
        self.assertEqual(context.post_calls, 2)
        self.assertEqual(context.dispose_calls, 1)
        self.assertEqual(playwright.stop_calls, 1)

    def test_api_client_context_manager_closes_resources(self) -> None:
        context = _FakeRequestContext()
        playwright = _FakePlaywright(context)
        launcher = _FakeSyncPlaywright(playwright)

        with (
            TemporaryDirectory() as temp_dir,
            patch("src.tawreed.tawreed_api.sync_playwright", return_value=launcher),
        ):
            state_path = Path(temp_dir) / "state.json"
            state_path.write_text("{}", encoding="utf-8")
            with TawreedApiClient(
                "https://seller.tawreed.io/#/login",
                state_path,
                Path(temp_dir) / "missing.json",
            ) as client:
                client.search_products("PANADOL")

        self.assertEqual(context.dispose_calls, 1)
        self.assertEqual(playwright.stop_calls, 1)


if __name__ == "__main__":
    unittest.main()
