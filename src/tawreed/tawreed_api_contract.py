"""Tawreed API endpoint contract persistence, discovery, and defaults."""

from __future__ import annotations

import json
import time
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


# ============================================================================
# API Discovery
# ============================================================================

def begin_api_contract_capture(page) -> list[dict[str, Any]]:
    """Attach a lightweight request listener and return its capture buffer."""
    captured: list[dict[str, Any]] = []
    if on_event := getattr(page, "on", None):
        on_event("request", lambda request: _capture_request(request, captured))
    return captured


def save_api_contract_capture(
    captured: list[dict[str, Any]], path=DEFAULT_CONTRACT_PATH
) -> TawreedApiContract:
    """Persist captured endpoints merged with any existing local contract."""
    return save_contract_requests(captured, path)


def _capture_request(request, captured: list[dict[str, Any]]) -> None:
    if str(request.method).upper() != "POST":
        return
    url = str(request.url)
    if not contract_type(url):
        return
    captured.append({"url": url, "body": _request_body(request)})


def _request_body(request) -> dict[str, Any]:
    try:
        body = request.post_data_json
        return body() if callable(body) else body
    except Exception:
        return {}


# ============================================================================
# Enhanced API Discovery
# ============================================================================

def begin_detailed_api_capture(page) -> list[dict[str, Any]]:
    """Capture full request details including headers and complete payload.
    
    This captures ALL POST requests to help discover the correct API structure.
    """
    captured: list[dict[str, Any]] = []
    
    def capture_handler(request):
        """Capture detailed request information."""
        if request.method != "POST":
            return
        
        url = str(request.url).lower()
        if any(keyword in url for keyword in ["cart", "product", "shopping", "order"]):
            _capture_request_details(request, captured)
    
    if hasattr(page, "on"):
        page.on("request", capture_handler)
    
    return captured


def _capture_request_details(request, captured):
    """Capture request details to list."""
    try:
        post_data = request.post_data_json
    except Exception:
        post_data = None
    
    captured.append({
        "timestamp": time.time(), "url": request.url, "method": request.method,
        "headers": dict(request.all_headers()), "post_data": post_data,
        "resource_type": request.resource_type
    })
    
    return captured


def save_captured_requests(
    captured: list[dict[str, Any]],
    profile_key: str,
    label: str = "api_capture"
) -> Path:
    """Save captured requests to JSON file for analysis."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path("artifacts") / "api_discovery" / profile_key
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{label}_{timestamp}.json"
    output_file.write_text(json.dumps(captured, indent=2, ensure_ascii=False), encoding="utf-8")
    
    _print_capture_summary(len(captured), output_file)
    return output_file


def _print_capture_summary(count, output_file):
    """Print capture summary."""
    print(f"[API Discovery] Captured {count} requests")
    print(f"[API Discovery] Saved to: {output_file}")


def analyze_add_to_cart_payload(captured_file: Path) -> dict[str, Any]:
    """Analyze captured requests to find add-to-cart pattern."""
    captured = json.loads(captured_file.read_text(encoding="utf-8"))
    add_to_cart_requests = _filter_cart_requests(captured)
    
    if not add_to_cart_requests:
        return {"error": "No add-to-cart requests found"}
    
    return _build_analysis(add_to_cart_requests)


def _filter_cart_requests(captured):
    """Filter cart-related requests."""
    result = []
    for req in captured:
        url = req.get("url", "").lower()
        if "cart" in url and "add" in url or "items" in url:
            result.append(req)
    return result


def _build_analysis(requests):
    """Build analysis from cart requests."""
    return {
        "total_requests": len(requests),
        "urls": list(set(r["url"] for r in requests)),
        "sample_payload": requests[0].get("post_data"),
        "common_headers": _find_common_headers(requests),
        "payload_fields": _analyze_payload_structure(requests),
    }


def _find_common_headers(requests: list[dict]) -> dict[str, str]:
    """Find headers present in all requests."""
    if not requests:
        return {}
    
    # Start with first request's headers
    common = dict(requests[0].get("headers", {}))
    
    # Keep only headers present in all requests
    for req in requests[1:]:
        headers = req.get("headers", {})
        common = {k: v for k, v in common.items() if k in headers}
    
    return common


def _analyze_payload_structure(requests: list[dict]) -> dict:
    """Analyze payload structure across multiple requests."""
    if not requests:
        return {}
    
    all_fields = set()
    field_types = {}
    
    for req in requests:
        payload = req.get("post_data")
        if not payload or not isinstance(payload, dict):
            continue
        
        _collect_fields(payload, all_fields, field_types, prefix="")
    
    return {
        "all_fields": sorted(all_fields),
        "field_types": field_types,
    }


def _collect_fields(obj: Any, all_fields: set, field_types: dict, prefix: str):
    """Recursively collect all fields and their types."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            field_path = f"{prefix}.{key}" if prefix else key
            all_fields.add(field_path)
            
            if field_path not in field_types:
                field_types[field_path] = type(value).__name__
            
            if isinstance(value, (dict, list)):
                _collect_fields(value, all_fields, field_types, field_path)
    
    elif isinstance(obj, list) and obj:
        # Analyze first item in list
        _collect_fields(obj[0], all_fields, field_types, f"{prefix}[0]")


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
    "begin_api_contract_capture",
    "save_api_contract_capture",
    "begin_detailed_api_capture",
    "save_captured_requests",
    "analyze_add_to_cart_payload",
]
