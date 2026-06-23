"""Enhanced network capture tool for discovering correct API payloads."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


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
        
        # Capture cart-related and product-related requests
        if any(keyword in url for keyword in ["cart", "product", "shopping", "order"]):
            try:
                post_data = request.post_data_json
            except Exception:
                post_data = None
                
            captured.append({
                "timestamp": time.time(),
                "url": request.url,
                "method": request.method,
                "headers": dict(request.all_headers()),
                "post_data": post_data,
                "resource_type": request.resource_type,
            })
    
    if hasattr(page, "on"):
        page.on("request", capture_handler)
    
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
    
    output_file.write_text(
        json.dumps(captured, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    print(f"[API Discovery] Captured {len(captured)} requests")
    print(f"[API Discovery] Saved to: {output_file}")
    
    return output_file


def analyze_add_to_cart_payload(captured_file: Path) -> dict[str, Any]:
    """Analyze captured requests to find add-to-cart pattern."""
    captured = json.loads(captured_file.read_text(encoding="utf-8"))
    
    add_to_cart_requests = []
    for req in captured:
        url = req.get("url", "").lower()
        if "cart" in url and "add" in url or "items" in url:
            add_to_cart_requests.append(req)
    
    if not add_to_cart_requests:
        return {"error": "No add-to-cart requests found"}
    
    # Analyze the structure
    analysis = {
        "total_requests": len(add_to_cart_requests),
        "urls": list(set(r["url"] for r in add_to_cart_requests)),
        "sample_payload": add_to_cart_requests[0].get("post_data"),
        "common_headers": _find_common_headers(add_to_cart_requests),
        "payload_fields": _analyze_payload_structure(add_to_cart_requests),
    }
    
    return analysis


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
