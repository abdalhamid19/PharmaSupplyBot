"""Local Tawreed API endpoint contract persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tawreed_constants import PRODUCT_SEARCH_ENDPOINT

DEFAULT_CONTRACT_PATH = Path("state") / "tawreed_api_endpoints.json"


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
    add = _first_request(requests, ("carts/items/add", "items/add", "cart/add", "carts/add", "purchase/cart"))
    remove = _first_request(requests, ("cart/remove", "carts/remove", "delete"))
    submit = _first_request(requests, ("checkout", "submit", "confirm"))
    return TawreedApiContract(product.get("url", ""), _dict_or_none(product.get("body")), add.get("url", ""), _dict_or_none(add.get("body")), remove.get("url", ""), _dict_or_none(remove.get("body")), submit.get("url", ""), _dict_or_none(submit.get("body")))


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
