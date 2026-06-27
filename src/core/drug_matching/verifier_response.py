"""Response processing and conflict resolution for AI verifier."""

from typing import Any

from .verifier_helpers import (
    apply_conflict_penalty,
    apply_critical_conflicts,
    apply_reject_decision_override,
    hard_conflict_names,
    resolve_ai_conflicts,
)


def process_api_response(result: dict[str, Any]) -> dict[str, Any]:
    """Process and resolve conflicts in AI API response.

    This is the main entry point for response processing, which:
    1. Detects and resolves contradictions in AI response fields
    2. Applies hard conflict overrides for critical mismatches
    3. Handles decision vs is_correct contradictions
    4. Caps confidence based on conflict types

    Args:
        result: Raw result from AI API call

    Returns:
        Processed result with conflicts resolved
    """
    return resolve_ai_conflicts(result)


def apply_conflict_logic(result: dict[str, Any]) -> dict[str, Any]:
    """Apply all conflict resolution logic to an AI result.

    This is an alias for resolve_ai_conflicts for clarity in calling code.
    """
    return resolve_ai_conflicts(result)


__all__ = [
    "process_api_response",
    "apply_conflict_logic",
    "resolve_ai_conflicts",
    "hard_conflict_names",
    "apply_critical_conflicts",
    "apply_conflict_penalty",
    "apply_reject_decision_override",
]
