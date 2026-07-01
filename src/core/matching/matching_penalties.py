"""Lexical penalty helpers for safer Tawreed product matching."""

from __future__ import annotations

import re

from ..matching_types import (
    ALIAS_TO_CANONICAL,
    CONFLICT_GROUPS,
    CRITICAL_TOKENS,
    DISTINGUISHING_TOKENS,
)

_TOKEN_BOUNDARY_RE = re.compile(r"(?<=\d)(?=[A-Z])|(?<=[A-Z])(?=\d)")
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")
_SPACE_RE = re.compile(r"\s+")


def penalty_breakdown(
    query: str,
    candidate: str,
    critical_weight: float,
    distinguishing_weight: float,
    semantic_weight: float,
) -> dict[str, float]:
    """Return lexical penalty components for one query and candidate name."""
    details = _token_details(query, candidate)
    return {
        "critical_penalty": -critical_weight * len(details["missing_critical"]),
        "extra_token_penalty": -distinguishing_weight
        * len(details["extra_distinguishing"]),
        "semantic_penalty": -semantic_weight * len(details["conflicts"]),
    }


def compatibility_rejection_reason(query: str, candidate: str) -> str:
    """Return a deterministic rejection reason for unsafe lexical variants."""
    details = _token_details(query, candidate)
    if details["conflicts"]:
        return _conflict_reason(details["conflicts"])
    if details["extra_distinguishing"]:
        tokens = ", ".join(sorted(details["extra_distinguishing"]))
        return f"Candidate has unrequested distinguishing token: {tokens}"
    return ""


def canonical_tokens(value: str) -> set[str]:
    """Return normalized canonical English tokens for matching rule checks."""
    spaced = _TOKEN_BOUNDARY_RE.sub(" ", str(value).upper())
    normalized = _SPACE_RE.sub(" ", _NON_ALNUM_RE.sub(" ", spaced))
    return {ALIAS_TO_CANONICAL.get(token, token) for token in normalized.split()}


def _token_details(
    query: str, candidate: str
) -> dict[str, set[tuple[str, str]] | set[str]]:
    query_tokens = canonical_tokens(query)
    candidate_tokens = canonical_tokens(candidate)
    query_critical = query_tokens & CRITICAL_TOKENS
    candidate_critical = candidate_tokens & CRITICAL_TOKENS
    return {
        "missing_critical": query_critical - candidate_critical,
        "extra_distinguishing": (candidate_tokens - query_tokens)
        & DISTINGUISHING_TOKENS,
        "conflicts": _semantic_conflicts(query_tokens, candidate_tokens),
    }


def _semantic_conflicts(
    query_tokens: set[str], candidate_tokens: set[str]
) -> set[tuple[str, str]]:
    conflicts: set[tuple[str, str]] = set()
    for group in CONFLICT_GROUPS:
        query_group = query_tokens & group
        candidate_group = candidate_tokens & group
        conflicts.update(
            (left, right) for left in query_group for right in candidate_group
        )
    return {(left, right) for left, right in conflicts if left != right}


def _conflict_reason(conflicts: set[tuple[str, str]]) -> str:
    conflict_text = ", ".join(f"{left} vs {right}" for left, right in sorted(conflicts))
    return f"Semantic token conflict: {conflict_text}"
