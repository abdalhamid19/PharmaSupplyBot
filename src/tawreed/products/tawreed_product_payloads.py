"""Shared product-response parsing for API and browser search transports."""

from __future__ import annotations

from typing import Any

from ..tawreed_constants import NESTED_NAME_KEYS, NESTED_STORE_KEYS, STORE_NAME_KEYS

_PRODUCT_LIST_KEYS = (
    "data",
    "content",
    "items",
    "products",
    "result",
    "results",
    "storeProducts",
)


def product_candidates_from_payload(payload: Any) -> list[dict[str, Any]]:
    """Return enriched product rows from an API or browser response payload."""
    return [_enrich_candidate(candidate) for candidate in _product_dicts(payload)]


def _product_dicts(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [candidate for candidate in payload if _is_product_dict(candidate)]
    if not isinstance(payload, dict):
        return []
    if _is_product_dict(payload):
        return [payload]
    return _first_nested_product_list(payload)


def _first_nested_product_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in _PRODUCT_LIST_KEYS:
        candidates = _product_dicts(payload.get(key))
        if candidates:
            return candidates
    return []


def _is_product_dict(candidate: Any) -> bool:
    return isinstance(candidate, dict) and bool(
        candidate.get("productName") or candidate.get("productNameEn")
    )


def _enrich_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    if candidate.get("companyName"):
        return candidate
    company_name = _extract_company_name(candidate)
    if company_name:
        candidate["companyName"] = company_name
    return candidate


def _extract_company_name(candidate: dict[str, Any]) -> str:
    for key in STORE_NAME_KEYS:
        value = str(candidate.get(key) or "").strip()
        if value:
            return value
    for object_key in NESTED_STORE_KEYS:
        nested = candidate.get(object_key)
        if isinstance(nested, dict):
            for name_key in NESTED_NAME_KEYS:
                value = str(nested.get(name_key) or "").strip()
                if value:
                    return value
    return ""


__all__ = ["product_candidates_from_payload"]
