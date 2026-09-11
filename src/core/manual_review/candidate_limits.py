"""Shared semantics for candidate limits across save, discovery, and UI."""

from __future__ import annotations


DEFAULT_CANDIDATE_LIMIT = 5


def normalize_candidate_limit(value: object, default: int = DEFAULT_CANDIDATE_LIMIT) -> int:
    """Return one positive candidate limit, falling back on invalid input."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = int(default)
    return max(1, parsed)
