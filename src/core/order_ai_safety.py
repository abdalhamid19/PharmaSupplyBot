"""Local safety checks for live-order AI decisions."""
from __future__ import annotations

from .candidate_identity import candidate_has_store_product_id
from .drug_matching.normalizer import components_match, parse_drug
from .order_ai_records import candidate_name


def local_match_rejection(item, match) -> str:
    """Return why an AI-selected match must not become orderable."""
    if not candidate_has_store_product_id(match.data):
        return "missing storeProductId"
    requested = parse_drug(item.name)
    offered = parse_drug(candidate_name(match.data))
    if requested.brand and offered.brand:
        is_match, reason = components_match(requested, offered)
        if not is_match:
            return f"component mismatch: {reason}"
    return ""


def local_rejection_result(reason: str) -> dict[str, object]:
    """Return a verifier-shaped result for a local safety rejection."""
    return {
        "is_correct": False,
        "reason": f"local_safety: {reason}",
        "confidence": 0.0,
    }
