"""Candidate identity helpers shared by matching, AI, and artifacts."""

from __future__ import annotations

from typing import Any


def candidate_store_product_id(candidate: dict[str, Any]) -> str:
    """Return the stable orderable Tawreed candidate id when one is available."""
    for key in ("storeProductId", "store_product_id", "id"):
        value = candidate.get(key)
        normalized = _normalized_id(value)
        if normalized:
            return normalized
    return ""


def candidate_has_store_product_id(candidate: dict[str, Any]) -> bool:
    """Return whether the candidate has an orderable Tawreed id."""
    return bool(candidate_store_product_id(candidate))


def _normalized_id(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "none", "nan", "null"}:
        return ""
    return text[:-2] if text.endswith(".0") else text
