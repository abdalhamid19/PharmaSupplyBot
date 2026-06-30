"""Enhanced API discovery for Tawreed."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .tawreed_api_contract_base import DEFAULT_CONTRACT_PATH


def begin_api_contract_capture(page) -> list[dict[str, Any]]:
    """Attach a lightweight request listener and return its capture buffer."""
    from ..tawreed_product_search import _search_response_pattern
    captured: list[dict[str, Any]] = []
    if on_event := getattr(page, "on", None):
        on_event("request", lambda request: _capture_request(request, captured))
    return captured


def save_api_contract_capture(
    captured: list[dict[str, Any]], path=DEFAULT_CONTRACT_PATH
) -> dict[str, Any]:
    """Persist captured endpoints merged with any existing local contract."""
    from .tawreed_api_contract_base import save_contract_requests
    return save_contract_requests(captured, path)


def _capture_request(request, captured: list[dict[str, Any]]) -> None:
    from .tawreed_api_contract_base import contract_type
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
    "begin_api_contract_capture",
    "save_api_contract_capture",
    "begin_detailed_api_capture",
    "save_captured_requests",
    "analyze_add_to_cart_payload",
]
