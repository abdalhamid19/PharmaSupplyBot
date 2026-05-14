"""Candidate identity helpers shared by matching, AI, and artifacts."""

from __future__ import annotations

from typing import Any

ORDERABLE_ID_KEYS = (
    "storeProductId",
    "store_product_id",
    "productStoreId",
    "product_store_id",
)
NESTED_CANDIDATE_KEYS = ("metadata", "meta", "raw", "_raw", "api", "candidate")


def candidate_store_product_id(candidate: dict[str, Any]) -> str:
    """Return the stable orderable Tawreed candidate id when one is available."""
    direct = _first_orderable_id(candidate)
    if direct:
        return direct
    for key in NESTED_CANDIDATE_KEYS:
        nested = candidate.get(key)
        if isinstance(nested, dict):
            nested_id = _first_orderable_id(nested)
            if nested_id:
                return nested_id
    return ""


def candidate_has_store_product_id(candidate: dict[str, Any]) -> bool:
    """Return whether the candidate has an orderable Tawreed id."""
    return bool(candidate_store_product_id(candidate))


def _normalized_id(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "none", "nan", "null"}:
        return ""
    return text[:-2] if text.endswith(".0") else text


def _first_orderable_id(candidate: dict[str, Any]) -> str:
    for key in ORDERABLE_ID_KEYS:
        normalized = _normalized_id(candidate.get(key))
        if normalized:
            return normalized
    return ""
