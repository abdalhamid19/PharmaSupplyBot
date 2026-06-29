"""Main Tawreed API client class and context management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .tawreed_api_contract import DEFAULT_CONTRACT_PATH, load_api_contract, product_search_url, TawreedApiUnavailable
from .tawreed_auth import customer_id_from_state
from .tawreed_api_operations import (
    search_products,
    get_store_details,
    add_to_cart,
    remove_cart_item,
    submit_order,
)
from .tawreed_api_http import _api_origin, _auth_headers_from_state, _is_trusted_add_to_cart_url


# ============================================================================
# Main API Client
# ============================================================================

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
        
        # Extract customer ID from token
        self.customer_id = customer_id_from_state(state_path)

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

    # Delegate operations to helper methods
    def search_products(self, query: str) -> list[dict[str, Any]]:
        """Return product candidates from a discovered API search endpoint."""
        return search_products(self, query)

    def contract_field_available(self, field: str) -> bool:
        """Return whether a required API field is available or safely defaulted."""
        if field == "product_search_url":
            return bool(product_search_url(self.contract))
        if field == "add_to_cart_url":
            return _is_trusted_add_to_cart_url(self.contract.add_to_cart_url)
        return bool(getattr(self.contract, field, ""))

    def get_store_details(self, product_id: Any) -> list[dict[str, Any]]:
        """Fetch multiple stores for a product via API."""
        return get_store_details(self, product_id)

    def add_to_cart(self, match: Any, quantity: int) -> None:
        """Add a matched product to the cart through a discovered API endpoint."""
        add_to_cart(self, match, quantity)

    def remove_cart_item(self, item: Any) -> None:
        """Remove one cart item through a discovered API endpoint."""
        remove_cart_item(self, item)

    def submit_order(self) -> None:
        """Submit an order through API only when the contract explicitly supports it."""
        submit_order(self)

    def _ensure_request_context(self):
        """Return a reusable Playwright APIRequestContext for this client."""
        if self._request_context is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._request_context = self._playwright.request.new_context(
                storage_state=str(self.state_path),
                base_url=_api_origin(self.base_url),
                extra_http_headers=_auth_headers_from_state(self.state_path),
            )
        return self._request_context


__all__ = ["TawreedApiUnavailable", "TawreedApiClient"]
