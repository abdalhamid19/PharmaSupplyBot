"""Tawreed API endpoint contract persistence and discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tawreed_constants import PRODUCT_SEARCH_ENDPOINT

DEFAULT_CONTRACT_PATH = Path("state") / "tawreed_api_endpoints.json"


# ============================================================================
# Exceptions
# ============================================================================

class TawreedApiUnavailable(RuntimeError):
    """Raised when Tawreed API endpoints are not available or fail."""


@dataclass(frozen=True)
class TawreedApiContract:
    """Discovered Tawreed API endpoint contract."""

    product_search_url: str = ""
    product_search_body: dict[str, Any] | None = None
    add_to_cart_url: str = ""
    add_to_cart_body: dict[str, Any] | None = None
    remove_cart_url: str = ""
    remove_cart_body: dict[str, Any] | None = None
    submit_order_url: str = ""
    submit_order_body: dict[str, Any] | None = None


# ============================================================================
# Contract Loading/Saving
# ============================================================================

def load_api_contract(path: Path = DEFAULT_CONTRACT_PATH) -> TawreedApiContract:
    """Load the locally discovered Tawreed API contract when available."""
    if not path.exists():
        return TawreedApiContract()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TawreedApiContract(
        product_search_url=str(payload.get("product_search_url") or ""),
        product_search_body=_dict_or_none(payload.get("product_search_body")),
        add_to_cart_url=str(payload.get("add_to_cart_url") or ""),
        add_to_cart_body=_dict_or_none(payload.get("add_to_cart_body")),
        remove_cart_url=str(payload.get("remove_cart_url") or ""),
        remove_cart_body=_dict_or_none(payload.get("remove_cart_body")),
        submit_order_url=str(payload.get("submit_order_url") or ""),
        submit_order_body=_dict_or_none(payload.get("submit_order_body"))
    )


def save_discovered_api_contract(
    captured_requests: list[dict[str, Any]], path: Path = DEFAULT_CONTRACT_PATH
) -> TawreedApiContract:
    """Persist a best-effort API contract from captured Tawreed network requests."""
    contract = _contract_from_requests(captured_requests)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_contract_payload(contract), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return contract


def _contract_from_requests(requests: list[dict[str, Any]]) -> TawreedApiContract:
    product = _first_request(requests, (PRODUCT_SEARCH_ENDPOINT, "product-search"))
    add = _first_request(
        requests,
        ("carts/items/add", "items/add", "cart/add", "carts/add", "purchase/cart")
    )
    remove = _first_request(requests, ("cart/remove", "carts/remove", "delete"))
    submit = _first_request(requests, ("checkout", "submit", "confirm"))
    return TawreedApiContract(
        product.get("url", ""),
        _dict_or_none(product.get("body")),
        add.get("url", ""),
        _dict_or_none(add.get("body")),
        remove.get("url", ""),
        _dict_or_none(remove.get("body")),
        submit.get("url", ""),
        _dict_or_none(submit.get("body"))
    )


def _first_request(
    requests: list[dict[str, Any]], markers: tuple[str, ...]
) -> dict[str, Any]:
    for request in requests:
        url = str(request.get("url") or "").lower()
        if any(marker.lower() in url for marker in markers):
            return request
    return {}


def _contract_payload(contract: TawreedApiContract) -> dict[str, Any]:
    return {
        "product_search_url": contract.product_search_url,
        "product_search_body": contract.product_search_body or {},
        "add_to_cart_url": contract.add_to_cart_url,
        "add_to_cart_body": contract.add_to_cart_body or {},
        "remove_cart_url": contract.remove_cart_url,
        "remove_cart_body": contract.remove_cart_body or {},
        "submit_order_url": contract.submit_order_url,
        "submit_order_body": contract.submit_order_body or {},
    }


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


# ============================================================================
# Contract Merging
# ============================================================================

_CONTRACT_MARKERS = {
    "product": (PRODUCT_SEARCH_ENDPOINT, "product-search"),
    "add": (
        "cart/add",
        "carts/add",
        "add-to-cart",
        "addtocart",
        "add-cart",
        "cart/add-item",
        "carts/items/add",
        "items/add",
        "purchase/carts",
        "shopping-cart",
    ),
    "remove": ("cart/remove", "carts/remove", "remove-from-cart", "removeitem"),
    "submit": ("checkout", "submit", "confirm", "orders/submit", "order/confirm"),
}


def save_contract_requests(
    requests: list[dict[str, Any]], path: Path = DEFAULT_CONTRACT_PATH
) -> TawreedApiContract:
    """Persist captured endpoint requests merged with the existing contract."""
    contract = _merge_contracts(load_api_contract(path), _contract_from_requests_merged(requests))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_payload(contract), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return contract


def contract_type(url: object) -> str:
    """Return the contract field group represented by one API URL."""
    text = str(url or "").lower()
    for kind, markers in _CONTRACT_MARKERS.items():
        if any(marker.lower() in text for marker in markers):
            return kind
    return ""


def _contract_from_requests_merged(requests: list[dict[str, Any]]) -> TawreedApiContract:
    grouped = {kind: _first_request_merged(requests, kind) for kind in _CONTRACT_MARKERS}
    return TawreedApiContract(
        grouped["product"].get("url", ""),
        _dict_or_none(grouped["product"].get("body")),
        grouped["add"].get("url", ""),
        _dict_or_none(grouped["add"].get("body")),
        grouped["remove"].get("url", ""),
        _dict_or_none(grouped["remove"].get("body")),
        grouped["submit"].get("url", ""),
        _dict_or_none(grouped["submit"].get("body")),
    )


def _first_request_merged(requests: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    return next((request for request in requests if contract_type(request.get("url")) == kind), {})


def _merge_contracts(existing, discovered) -> TawreedApiContract:
    return TawreedApiContract(
        discovered.product_search_url or existing.product_search_url,
        discovered.product_search_body or existing.product_search_body,
        discovered.add_to_cart_url or existing.add_to_cart_url,
        discovered.add_to_cart_body or existing.add_to_cart_body,
        discovered.remove_cart_url or existing.remove_cart_url,
        discovered.remove_cart_body or existing.remove_cart_body,
        discovered.submit_order_url or existing.submit_order_url,
        discovered.submit_order_body or existing.submit_order_body,
    )


def _payload(contract: TawreedApiContract) -> dict[str, Any]:
    payload = {}
    for key, value in vars(contract).items():
        payload[key] = value or ({} if key.endswith("_body") else "")
    return payload


# ============================================================================
# Default Values
# ============================================================================

DEFAULT_PRODUCT_SEARCH_URL = (
    f"/rest/v2/{PRODUCT_SEARCH_ENDPOINT}?sort=productName,asc&page=0&size=50"
)
DEFAULT_PRODUCT_SEARCH_BODY = {
    "mode": "error",
    "langCode": "ar",
    "data": {"displayType": 1},
}


def product_search_url(contract) -> str:
    """Return a discovered or safe default product-search endpoint."""
    return str(getattr(contract, "product_search_url", "") or DEFAULT_PRODUCT_SEARCH_URL)


def product_search_body(contract) -> dict[str, Any]:
    """Return a discovered or safe default product-search body."""
    return getattr(contract, "product_search_body", None) or DEFAULT_PRODUCT_SEARCH_BODY


__all__ = [
    "DEFAULT_CONTRACT_PATH",
    "TawreedApiContract",
    "TawreedApiUnavailable",
    "load_api_contract",
    "save_discovered_api_contract",
    "save_contract_requests",
    "contract_type",
    "DEFAULT_PRODUCT_SEARCH_URL",
    "DEFAULT_PRODUCT_SEARCH_BODY",
    "product_search_url",
    "product_search_body",
]
