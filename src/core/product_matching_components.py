"""Component matching and rejection logic for product matching."""

from __future__ import annotations

from typing import Any

from .drug_matching.normalizer import components_match, parse_drug


def _candidate_component_rejection(query: str, candidate: dict[str, Any]) -> str:
    """Return a rejection reason when parsed drug components are incompatible."""
    from .product_matching_scoring import _candidate_english_name

    candidate_name = _candidate_english_name(candidate)
    if not candidate_name:
        return ""
    requested = parse_drug(query)
    offered = parse_drug(candidate_name)
    offered.is_synthetic = bool(candidate.get("productNameEnSynthetic"))
    if not requested.brand or not offered.brand:
        return ""
    is_match, reason = components_match(requested, offered)
    if is_match:
        return ""
    return f"Component mismatch: {reason}"
