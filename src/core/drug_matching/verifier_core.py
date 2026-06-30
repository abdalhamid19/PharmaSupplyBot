"""Core helper functions for AI verifier module.

This module consolidates all helper functions from the refactored submodules:
- Constants for failure limits and conflict types
- AI conflict resolution functions
- Utility functions
- Re-exports from verifier_core_extract and verifier_core_format
"""

from __future__ import annotations

from typing import Any

from .verifier_core_extract import (
    api_error_code,
    extract_json,
    infer_is_correct,
    json_with_safe_defaults,
    loads_json_object,
)
from .verifier_core_format import (
    component_context,
    format_candidate,
    route_from_norm,
)

# ============================================================================
# Constants
# ============================================================================

_TRANSIENT_COMBO_FAILURE_LIMIT = 2
_PERMANENT_PARSE_FAILURES = frozenset((
    "invalid_json",
    "null_content",
    "json_generation_failed",
))
# AI-reported conflicts that override is_correct=True → force reject.
_HARD_CONFLICT_REJECT = frozenset((
    "different_strength",
    "different_dosage",
    "different_active_ingredient",
    "different_concentration",
    "different_route",
))
# AI-reported conflicts that lower confidence but don't force reject.
_HARD_CONFLICT_PENALTY = frozenset((
    "different_form",
    "different_quantity",
    "different_volume",
    "different_brand",
    "different_flavor",
    "different_age_group",
    "different_pack_size",
))

# ============================================================================
# AI Conflict Resolution
# ============================================================================

def resolve_ai_conflicts(result: dict[str, Any]) -> dict[str, Any]:
    """Detect and resolve contradictions in AI response fields.

    1. If hard_conflicts contain a critical mismatch → force is_correct=False.
    2. If decision='reject' but is_correct=True → trust decision, set is_correct=False.
    3. If hard_conflicts contain non-critical items → cap confidence.
    """
    hard_lower = hard_conflict_names(result)
    apply_critical_conflicts(result, hard_lower)
    apply_conflict_penalty(result, hard_lower)
    apply_reject_decision_override(result)
    return result


def hard_conflict_names(result: dict[str, Any]) -> set[str]:
    """Extract and normalize hard conflict names from AI result."""
    hard = result.get("hard_conflicts") or []
    if isinstance(hard, str):
        hard = [h.strip() for h in hard.split(",") if h.strip()]
    return {h.lower().replace(" ", "_") for h in hard}


def apply_critical_conflicts(result: dict[str, Any], hard_lower: set[str]) -> None:
    """Apply critical conflict overrides that force is_correct=False."""
    critical = hard_lower & _HARD_CONFLICT_REJECT
    if critical and result.get("is_correct"):
        result["is_correct"] = False
        conflict_text = ", ".join(sorted(critical))
        reason = result.get("reason", "")
        result["reason"] = (
            f"hard_conflict_override({conflict_text}); {reason}"
            if reason else f"hard_conflict_override({conflict_text})"
        )
        result["confidence"] = min(result.get("confidence", 0.0), 0.55)


def apply_conflict_penalty(result: dict[str, Any], hard_lower: set[str]) -> None:
    """Apply confidence penalty for non-critical hard conflicts."""
    penalty = hard_lower & _HARD_CONFLICT_PENALTY
    if penalty and result.get("is_correct"):
        result["confidence"] = min(result.get("confidence", 0.0), 0.72)


def apply_reject_decision_override(result: dict[str, Any]) -> None:
    """Override is_correct to False when AI decision is 'reject'."""
    decision = str(result.get("decision", "")).lower().strip()
    if decision == "reject" and result.get("is_correct"):
        result["is_correct"] = False
        reason = result.get("reason", "")
        result["reason"] = (
            f"decision_reject_override; {reason}" if reason
            else "decision_reject_override"
        )
        result["confidence"] = min(result.get("confidence", 0.0), 0.6)

# ============================================================================
# Utility Functions
# ============================================================================

def coerce_best_index(value, max_index: int) -> tuple[int, bool]:
    """Return a safe candidate index and whether the source value was valid."""
    if isinstance(value, bool) or value is None:
        return 0, False
    if isinstance(value, int):
        idx = value
    elif isinstance(value, str) and value.strip().isdigit():
        idx = int(value.strip())
    else:
        return 0, False
    if 0 <= idx <= max_index:
        return idx, True
    return 0, False


def fallback_from_unparseable_response(text: str, model: str) -> dict[str, Any]:
    """Return a fallback verification result when AI response cannot be parsed."""
    return {
        "is_correct": False,
        "agree": False,
        "reason": f"invalid_json:{text[:180]}",
        "confidence": 0.4,
        "model_used": model,
        "parse_failed": True,
    }


def normalize_verify_item(
    item: tuple,
) -> tuple[str, str, str, int, str, str, object, object]:
    """Support old verify items plus optional score/method context."""
    if len(item) == 3:
        drug_a, drug_b, row_idx = item
        return drug_a, drug_b, "", row_idx, "", "", None, None
    if len(item) == 4:
        drug_a, drug_b, drug_b_ar, row_idx = item
        return drug_a, drug_b, drug_b_ar, row_idx, "", "", None, None
    if len(item) == 6:
        drug_a, drug_b, drug_b_ar, row_idx, score, method = item
        return drug_a, drug_b, drug_b_ar, row_idx, score, method, None, None
    drug_a, drug_b, drug_b_ar, row_idx = item[:4]
    score, method = item[4], item[5]
    inventory_price, candidate_price = item[6], item[7]
    return (
        drug_a, drug_b, drug_b_ar, row_idx, score, method,
        inventory_price, candidate_price,
    )


def normalize_review_item(item: tuple) -> tuple:
    """Support review items with optional inventory/candidate prices."""
    if len(item) == 8:
        return (*item, None, None)
    return item


__all__ = [
    # Constants
    "_TRANSIENT_COMBO_FAILURE_LIMIT",
    "_PERMANENT_PARSE_FAILURES",
    "_HARD_CONFLICT_REJECT",
    "_HARD_CONFLICT_PENALTY",
    # JSON parsing (re-exported)
    "extract_json",
    "json_with_safe_defaults",
    "loads_json_object",
    "infer_is_correct",
    "api_error_code",
    # Conflict resolution
    "resolve_ai_conflicts",
    "hard_conflict_names",
    "apply_critical_conflicts",
    "apply_conflict_penalty",
    "apply_reject_decision_override",
    # Formatting (re-exported)
    "route_from_norm",
    "component_context",
    "format_candidate",
    # Utilities
    "coerce_best_index",
    "fallback_from_unparseable_response",
    "normalize_verify_item",
    "normalize_review_item",
]
