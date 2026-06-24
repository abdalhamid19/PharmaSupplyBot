"""Merge browser-captured Tawreed API requests into the local contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .tawreed_api_contract import DEFAULT_CONTRACT_PATH, TawreedApiContract, load_api_contract
from .tawreed_constants import PRODUCT_SEARCH_ENDPOINT

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
    contract = _merge_contracts(load_api_contract(path), _contract_from_requests(requests))
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


def _contract_from_requests(requests: list[dict[str, Any]]) -> TawreedApiContract:
    grouped = {kind: _first_request(requests, kind) for kind in _CONTRACT_MARKERS}
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


def _first_request(requests: list[dict[str, Any]], kind: str) -> dict[str, Any]:
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


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _payload(contract: TawreedApiContract) -> dict[str, Any]:
    payload = {}
    for key, value in vars(contract).items():
        payload[key] = value or ({} if key.endswith("_body") else "")
    return payload
