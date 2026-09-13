"""Tests for optional Tawreed API execution support."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.core.config.config_models import MatchingConfig
from src.core.manual_review.manual_review_runtime import (
    manual_review_cache_context,
    preload_manual_review_decisions,
)
from src.core.manual_review.manual_review_store import ManualReviewDecision, ManualReviewStore
from src.core.utils.excel import Item
from src.tawreed.api.tawreed_api_client import (
    TawreedApiClient,
    TawreedApiUnavailable,
    _auth_headers_from_state,
)
from src.tawreed.api.tawreed_api_contract import (
    load_api_contract,
    save_discovered_api_contract,
)
from src.tawreed.api.tawreed_api_flow import _submit_order_if_enabled
from src.tawreed.api.tawreed_api_flow_matching import _api_match_decision


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


class _ConfigurableResponse:
    ok = True
    status = 200

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self):
        return self._payload


class _RecordingContext:
    """API request context that records the last POST and returns a fixed body."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.last_url = None
        self.last_body = None

    def post(self, url, data=None, timeout=None, **kwargs):
        self.last_url = url
        self.last_body = data
        return _ConfigurableResponse(self._payload)

    def dispose(self) -> None:
        pass


class _StatusResponse:
    def __init__(self, status: int, payload: dict) -> None:
        self.ok = 200 <= status < 300
        self.status = status
        self.status_text = "Unauthorized" if status == 401 else "OK"
        self._payload = payload

    def json(self):
        return self._payload


class _SequencedContext:
    def __init__(self, response: _StatusResponse) -> None:
        self.response = response
        self.dispose_calls = 0

    def post(self, *args, **kwargs):
        return self.response

    def dispose(self) -> None:
        self.dispose_calls += 1


class _SequencedRequestFactory:
    def __init__(self, contexts: list[_SequencedContext]) -> None:
        self.contexts = contexts
        self.new_context_calls = 0

    def new_context(self, **kwargs):
        context = self.contexts[self.new_context_calls]
        self.new_context_calls += 1
        return context


class _SequencedPlaywright:
    def __init__(self, contexts: list[_SequencedContext]) -> None:
        self.request = _SequencedRequestFactory(contexts)
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


class _SequencedSyncPlaywright:
    def __init__(self, playwright: _SequencedPlaywright) -> None:
        self.playwright = playwright

    def start(self):
        return self.playwright


def _add_to_cart_client(temp_dir: str, response_payload: dict):
    """Return an API client wired to a recording context and add contract."""
    state_path = Path(temp_dir) / "state.json"
    state_path.write_text("{}", encoding="utf-8")
    contract_path = Path(temp_dir) / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "add_to_cart_url": "https://api.tawreed.io/rest/v2/shopping/carts/items/add",
                "add_to_cart_body": {"mode": "error", "langCode": "ar", "data": {}},
            }
        ),
        encoding="utf-8",
    )
    client = TawreedApiClient(
        "https://seller.tawreed.io/#/login", state_path, contract_path
    )
    context = _RecordingContext(response_payload)
    client._request_context = context
    client.customer_id = 22823
    return client, context


class TawreedApiTests(unittest.TestCase):
    """Validate local API contract parsing and safe unavailable behavior."""

    def test_api_matching_does_not_force_legacy_man_approval_for_milga(self) -> None:
        item = Item("92558", "LIMITLESS MILGA MAX 30 TABS", 17)
        man_candidate = {
            "storeProductId": "2145610",
            "productNameEn": "LIMITLESS MAN MAX 30 TABS",
            "availableQuantity": 39,
        }
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "manual-review.sqlite3"
            ManualReviewStore(db_path).upsert(
                ManualReviewDecision(
                    item.code,
                    item.name,
                    True,
                    man_candidate["storeProductId"],
                    correct_product_name=man_candidate["productNameEn"],
                    run_id="20260825_1005",
                    manual_decision="approved_match",
                    matching_source="legacy-unknown",
                    supplier_scope_key="legacy-unknown",
                )
            )
            bot = SimpleNamespace(
                config=SimpleNamespace(matching=MatchingConfig()),
            )
            with patch(
                "src.core.manual_review.manual_review_store.DEFAULT_MANUAL_REVIEW_DB",
                db_path,
            ):
                cache = preload_manual_review_decisions([item])
                with manual_review_cache_context(cache):
                    decision = _api_match_decision(
                        bot,
                        item,
                        [(item.name, [man_candidate])],
                    )

        self.assertIsNone(decision.best_match)
        self.assertIn("MILGA", decision.final_reason)
        self.assertIn("MAN", decision.final_reason)

    def test_load_missing_contract_disables_mutating_api(self) -> None:
        with TemporaryDirectory() as temp_dir:
            client = TawreedApiClient(
                "https://seller.tawreed.io/#/login",
                Path(temp_dir) / "wardany.json",
                Path(temp_dir) / "missing.json",
            )

        with self.assertRaises(TawreedApiUnavailable):
            client.add_to_cart(object(), 1)

    def test_body_with_match_builds_discovered_add_payload(self) -> None:
        from types import SimpleNamespace

        from src.tawreed.api.tawreed_api_payloads import body_with_match

        match = SimpleNamespace(data={"storeProductId": 2066374})
        payload = body_with_match(
            {"mode": "error", "langCode": "ar", "data": {"productId": None}},
            match,
            3,
        )

        self.assertEqual(payload["mode"], "all")
        self.assertEqual(payload["langCode"], "ar")
        self.assertEqual(
            payload["data"],
            {
                "customerId": None,
                "storeProductId": 2066374,
                "quantity": 3,
                "typeId": 1,
            },
        )

    def test_add_to_cart_posts_discovered_add_endpoint_with_customer_id(self) -> None:
        from types import SimpleNamespace

        match = SimpleNamespace(data={"storeProductId": 2066374})
        with TemporaryDirectory() as temp_dir:
            client, context = _add_to_cart_client(
                temp_dir, {"data": [{"storeProductId": 2066374}], "status": 200}
            )
            client.add_to_cart(match, 2)

        self.assertTrue(context.last_url.endswith("/shopping/carts/items/add"))
        self.assertEqual(context.last_body["mode"], "all")
        self.assertEqual(context.last_body["data"]["storeProductId"], 2066374)
        self.assertEqual(context.last_body["data"]["quantity"], 2)
        self.assertEqual(context.last_body["data"]["typeId"], 1)
        self.assertEqual(context.last_body["data"]["customerId"], 22823)

    def test_add_to_cart_raises_when_response_has_no_cart_data(self) -> None:
        from types import SimpleNamespace

        match = SimpleNamespace(data={"storeProductId": 2066374})
        with TemporaryDirectory() as temp_dir:
            client, _context = _add_to_cart_client(
                temp_dir, {"message": None, "data": [], "status": 200}
            )

            with self.assertRaises(TawreedApiUnavailable):
                client.add_to_cart(match, 1)

    def test_add_to_cart_rejects_cart_read_endpoint(self) -> None:
        from dataclasses import replace
        from types import SimpleNamespace

        match = SimpleNamespace(data={"storeProductId": 2066374})
        read_url = "https://api.tawreed.io/rest/v2/shopping/carts/items"
        with TemporaryDirectory() as temp_dir:
            client, _context = _add_to_cart_client(temp_dir, {"data": [{"x": 1}]})
            client.contract = replace(client.contract, add_to_cart_url=read_url)

            self.assertFalse(client.contract_field_available("add_to_cart_url"))
            with self.assertRaises(TawreedApiUnavailable):
                client.add_to_cart(match, 1)

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

    def test_discovered_contract_prefers_carts_items_add_over_read_endpoint(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "contract.json"
            contract = save_discovered_api_contract(
                [
                    {
                        "url": "https://api.tawreed.io/rest/v2/shopping/carts/items",
                        "body": {"data": {"productId": None, "storesList": None}},
                    },
                    {
                        "url": "https://api.tawreed.io/rest/v2/shopping/carts/items/add",
                        "body": {
                            "mode": "all",
                            "data": {"storeProductId": 2066374, "typeId": 1},
                        },
                    },
                ],
                output,
            )

        self.assertTrue(contract.add_to_cart_url.endswith("/shopping/carts/items/add"))

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
            patch("playwright.sync_api.sync_playwright", return_value=launcher),
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
            patch("playwright.sync_api.sync_playwright", return_value=launcher),
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

    def test_api_client_refreshes_auth_and_retries_after_http_401(self) -> None:
        first = _SequencedContext(_StatusResponse(401, {"message": "expired"}))
        second = _SequencedContext(
            _StatusResponse(200, {"data": [{"productNameEn": "PANADOL"}]})
        )
        playwright = _SequencedPlaywright([first, second])
        refresh = Mock()

        with (
            TemporaryDirectory() as temp_dir,
            patch(
                "playwright.sync_api.sync_playwright",
                return_value=_SequencedSyncPlaywright(playwright),
            ),
        ):
            state_path = Path(temp_dir) / "state.json"
            state_path.write_text("{}", encoding="utf-8")
            contract_path = Path(temp_dir) / "contract.json"
            contract_path.write_text(
                json.dumps({"product_search_url": "/rest/v2/product-search"}),
                encoding="utf-8",
            )
            client = TawreedApiClient(
                "https://seller.tawreed.io/#/login",
                state_path,
                contract_path,
                auth_refresh=refresh,
            )

            results = client.search_products("PANADOL")
            client.close()

        self.assertEqual(results[0]["productNameEn"], "PANADOL")
        refresh.assert_called_once_with()
        self.assertEqual(playwright.request.new_context_calls, 2)
        self.assertEqual(first.dispose_calls, 1)


if __name__ == "__main__":
    unittest.main()
