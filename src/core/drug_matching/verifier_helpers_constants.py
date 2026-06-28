"""Constants for AI verifier helper functions."""

from __future__ import annotations

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

__all__ = [
    "_TRANSIENT_COMBO_FAILURE_LIMIT",
    "_PERMANENT_PARSE_FAILURES",
    "_HARD_CONFLICT_REJECT",
    "_HARD_CONFLICT_PENALTY",
]
