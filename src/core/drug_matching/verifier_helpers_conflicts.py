"""AI conflict resolution functions for verifier."""

from __future__ import annotations

from typing import Any

from .verifier_helpers_constants import _HARD_CONFLICT_REJECT, _HARD_CONFLICT_PENALTY


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
