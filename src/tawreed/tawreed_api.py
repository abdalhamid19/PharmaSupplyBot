"""Optional API execution client for Tawreed flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from .tawreed_api_contract import DEFAULT_CONTRACT_PATH, load_api_contract
from .tawreed_api_defaults import product_search_body, product_search_url
from .tawreed_api_payloads import body_with_item, body_with_match, body_with_query
from .tawreed_auth_tokens import access_token_from_state
from .tawreed_product_search import _api_candidates


class TawreedApiUnavailable(RuntimeError):
    """Raised when the requested Tawreed API operation is not safely available."""


class TawreedApiClient:
    """Small synchronous API client that reuses Playwright storage state."""

    def __init__(
        self,
        base_url: str,
        state_path: Path,
        contract_path: Path = DEFAULT_CONTRACT_PATH,
    ):
        """Create an API client bound to one authenticated storage-state file."""
        self.base_url = base_url
        self.state_path = state_path
        self.contract = load_api_contract(contract_path)
        self._playwright = None
        self._request_context = None

    def __enter__(self):
        """Return this client; the request context opens on the first API call."""
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Dispose Playwright resources created by this client."""
        self.close()

    def close(self) -> None:
        """Release the reusable API request context and Playwright driver."""
        if self._request_context is not None:
            self._request_context.dispose()
            self._request_context = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def warm_up(self) -> None:
        """Open the reusable request context before item timing starts."""
        self._ensure_request_context()

    def search_products(self, query: str) -> list[dict[str, Any]]:
        """Return product candidates from a discovered API search endpoint."""
        payload = self._post_json(
            product_search_url(self.contract),
            body_with_query(product_search_body(self.contract), query),
        )
        return _api_candidates(payload)

    def contract_field_available(self, field: str) -> bool:
        """Return whether a required API field is available or safely defaulted."""
        if field == "product_search_url":
            return bool(product_search_url(self.contract))
        return bool(getattr(self.contract, field, ""))

    def add_to_cart(self, match: Any, quantity: int) -> None:
        """Add a matched product to the cart through a discovered API endpoint."""
        if not self.contract.add_to_cart_url:
            raise TawreedApiUnavailable("No trusted Tawreed add-to-cart API contract.")
        
        payload = body_with_match(self.contract.add_to_cart_body or {}, match, quantity)
        self._post_json(self.contract.add_to_cart_url, payload)

    def remove_cart_item(self, item: Any) -> None:
        """Remove one cart item through a discovered API endpoint."""
        if not self.contract.remove_cart_url:
            raise TawreedApiUnavailable("No trusted Tawreed cart-removal API contract.")
        self._post_json(
            self.contract.remove_cart_url,
            body_with_item(self.contract.remove_cart_body or {}, item),
        )

    def submit_order(self) -> None:
        """Submit an order through API only when the contract explicitly supports it."""
        if not self.contract.submit_order_url:
            raise TawreedApiUnavailable("No trusted Tawreed order-submit API contract.")
        self._post_json(self.contract.submit_order_url, self.contract.submit_order_body or {})

    def _post_json(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST JSON with saved auth state without opening Chromium."""
        response = self._ensure_request_context().post(url, data=body, timeout=60_000)
        if not response.ok:
            raise TawreedApiUnavailable(
                f"Tawreed API returned HTTP {response.status}: {response.status_text}"
            )
        payload = response.json()
        
        # Check if response indicates failure
        if isinstance(payload, dict):
            status = payload.get("status")
            if status and status >= 400:
                raise TawreedApiUnavailable(
                    f"Tawreed API error {status}: {payload.get('message', 'Unknown error')}"
                )
        
        return payload if isinstance(payload, dict) else {"data": payload}

    def _ensure_request_context(self):
        """Return a reusable Playwright APIRequestContext for this client."""
        if self._request_context is None:
            self._playwright = sync_playwright().start()
            self._request_context = self._playwright.request.new_context(
                storage_state=str(self.state_path),
                base_url=_api_origin(self.base_url),
                extra_http_headers=_auth_headers_from_state(self.state_path),
            )
        return self._request_context


def _api_origin(base_url: str) -> str:
    if "seller.tawreed.io" in base_url:
        return "https://api.tawreed.io"
    return base_url.split("#/", 1)[0].rstrip("/")


def _auth_headers_from_state(state_path: Path) -> dict[str, str]:
    """Return Tawreed API auth headers extracted from Playwright storage state."""
    token = access_token_from_state(state_path)
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}
