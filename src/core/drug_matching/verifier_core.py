"""Core helper functions for AI verifier module.

This module consolidates all helper functions from the refactored submodules:
- Constants for failure limits and conflict types
- JSON parsing and extraction functions
- AI conflict resolution functions
- Candidate formatting and component context functions
"""

from __future__ import annotations

import json
import re
from typing import Any

from .normalizer import parse_drug

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
# JSON Parsing and Extraction
# ============================================================================

def extract_json(text: str) -> dict | None:
    """Extract JSON from model response, handling markdown code blocks and truncation."""
    if not isinstance(text, str) or not text:
        return None
    # Try direct parse
    if parsed := loads_json_object(text):
        return json_with_safe_defaults(parsed)
    # Try extracting from ```json ... ``` block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        if parsed := loads_json_object(m.group(1)):
            return json_with_safe_defaults(parsed)
    # Try finding first { ... } in text
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if m:
        if parsed := loads_json_object(m.group(0)):
            return json_with_safe_defaults(parsed)
    # Handle truncated JSON: find opening { and try to close it
    start = text.find("{")
    if start >= 0:
        fragment = text[start:]
        # Try adding closing braces
        for suffix in ["}", "\"}", "\"\n}"]:
            try:
                return json_with_safe_defaults(json.loads(fragment + suffix))
            except (json.JSONDecodeError, ValueError):
                continue
        # Last resort: extract key-value pairs with regex
        is_correct_m = re.search(r'"is_correct"\s*:\s*(true|false)', fragment, re.IGNORECASE)
        reason_m = re.search(r'"reason"\s*:\s*"([^"]*)"', fragment)
        confidence_m = re.search(r'"confidence"\s*:\s*([\d.]+)', fragment)
        if is_correct_m:
            return {
                "is_correct": is_correct_m.group(1).lower() == "true",
                "reason": reason_m.group(1) if reason_m else "",
                "confidence": float(confidence_m.group(1)) if confidence_m else 0.5,
            }
        decision_m = re.search(r'"decision"\s*:\s*"([^"]*)"', fragment)
        best_index_m = re.search(r'"best_index"\s*:\s*(\d+)', fragment)
        if decision_m or best_index_m:
            return {
                "decision": decision_m.group(1) if decision_m else "",
                "best_index": int(best_index_m.group(1)) if best_index_m else 0,
                "reason": reason_m.group(1) if reason_m else "",
                "confidence": float(confidence_m.group(1)) if confidence_m else 0.5,
            }
    return None


def json_with_safe_defaults(parsed: dict) -> dict:
    """Add conservative defaults when a repaired search response is incomplete."""
    if (
        ("decision" in parsed or "best_index" in parsed)
        and "confidence" not in parsed
    ):
        parsed["confidence"] = 0.5
    return parsed


def loads_json_object(text: str) -> dict | None:
    """Parse a JSON object after repairing common model formatting noise."""
    for candidate in (text, re.sub(r",\s*([}\]])", r"\1", text)):
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def infer_is_correct(text: str) -> bool:
    """Infer match correctness from text when JSON parsing fails."""
    lower = text.lower()
    # Strong reject signals
    for word in ["different brand", "not the same", "mismatch", "incorrect",
                 "wrong match", "different product", "different dosage",
                 "different form", "different quantity"]:
        if word in lower:
            return False
    # Strong accept signals
    for word in ["same product", "correct match", "identical", "is_correct",
                 "matching", "same brand", "same dosage"]:
        if word in lower:
            return True
    # Default: reject (safer for drug matching)
    return False


def api_error_code(status: int, text: str) -> str:
    """Extract API error code from HTTP status and response text."""
    lowered = text.lower()
    if status == 400 and (
        "failed_generation" in lowered
        or "failed to validate json" in lowered
        or '"code":"json_' in lowered
    ):
        return "json_generation_failed"
    return f"http_{status}"

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
# Candidate Formatting and Component Context
# ============================================================================

def route_from_norm(norm: str) -> str:
    """Extract route (IM/IV/SC) from normalized drug name."""
    words = set(norm.split())
    routes = set(words & {"IM", "IV", "SC"})
    if {"I", "M"} <= words:
        routes.add("IM")
    if {"I", "V"} <= words:
        routes.add("IV")
    if {"S", "C"} <= words:
        routes.add("SC")
    return "/".join(sorted(routes)) or "-"


def component_context(name: str) -> str:
    """Return formatted component context string for a drug name."""
    c = parse_drug(name)
    return (
        f"normalized='{c.normalized}', brand='{c.brand}', "
        f"dosage={c.dosage_nums or '-'}, qty='{c.qty or '-'}', "
        f"volume='{c.volume or '-'}', weight='{c.weight or '-'}', "
        f"form='{c.form or '-'}', flavor='{c.flavor or '-'}', "
        f"class='{c.product_class}', "
        f"route='{route_from_norm(c.normalized)}', "
        f"imported={'yes' if c.imported else 'no'}"
    )


def format_candidate(
    position: int, candidate: tuple[dict, float, int],
    inventory_price=None,
) -> str:
    """Format a candidate with position, score, price, and component context."""
    from .pricing import format_price, price_delta_text
    rec, score, _ = candidate[:3]
    review_reason = candidate[3] if len(candidate) > 3 else "ok"
    if review_reason == "ok":
        review_text = ""
    else:
        review_text = (
            f"\n   rule_review: candidate entered AI review despite {review_reason}; "
            "accept only if the products are truly equivalent"
        )
    candidate_price = rec.get("price")
    price_text = (
        f", candidate_price={format_price(candidate_price)}, "
        f"price_delta={price_delta_text(inventory_price, candidate_price)}"
    )
    return (
        f"{position}. {rec['product_name_en']} / "
        f"{rec.get('product_name_ar', '')} "
        f"(score={score:.1f}{price_text})\n"
        f"   parsed: {component_context(rec['product_name_en'])}"
        f"{review_text}"
    )

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
    # JSON parsing
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
    # Formatting
    "route_from_norm",
    "component_context",
    "format_candidate",
    # Utilities
    "coerce_best_index",
    "fallback_from_unparseable_response",
    "normalize_verify_item",
    "normalize_review_item",
]
