"""Helper functions for AI verifier module."""

from __future__ import annotations

from typing import Any

from .verifier_helpers_constants import (
    _TRANSIENT_COMBO_FAILURE_LIMIT,
    _PERMANENT_PARSE_FAILURES,
    _HARD_CONFLICT_REJECT,
    _HARD_CONFLICT_PENALTY,
)
from .verifier_helpers_parsing import (
    extract_json,
    json_with_safe_defaults,
    loads_json_object,
    infer_is_correct,
    api_error_code,
)
from .verifier_helpers_conflicts import (
    resolve_ai_conflicts,
    hard_conflict_names,
    apply_critical_conflicts,
    apply_conflict_penalty,
    apply_reject_decision_override,
)
from .verifier_helpers_formatting import (
    route_from_norm,
    component_context,
    format_candidate,
)


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
    "coerce_best_index",
    "api_error_code",
    "extract_json",
    "json_with_safe_defaults",
    "loads_json_object",
    "infer_is_correct",
    "resolve_ai_conflicts",
    "hard_conflict_names",
    "apply_critical_conflicts",
    "apply_conflict_penalty",
    "apply_reject_decision_override",
    "fallback_from_unparseable_response",
    "route_from_norm",
    "component_context",
    "format_candidate",
    "normalize_verify_item",
    "normalize_review_item",
    "_TRANSIENT_COMBO_FAILURE_LIMIT",
    "_PERMANENT_PARSE_FAILURES",
    "_HARD_CONFLICT_REJECT",
    "_HARD_CONFLICT_PENALTY",
]
