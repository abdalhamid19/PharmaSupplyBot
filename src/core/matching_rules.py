"""Acceptance rules and defaults for Tawreed product matching."""

from __future__ import annotations

from typing import Any

from ..config_models import MatchingConfig


def default_matching_config() -> MatchingConfig:
    """Return the built-in matching thresholds used when no config is supplied."""
    return MatchingConfig()


def acceptance_details(
    query: str,
    candidate: dict[str, Any],
    score: float,
    matching_config: MatchingConfig,
    helpers: tuple,
) -> tuple[bool, str, str]:
    """Return whether a match is acceptable plus acceptance and rejection reasons."""
    match_context = _match_context(
        query,
        candidate,
        helpers,
    )
    for accepted, reason in _acceptance_checks(score, matching_config, match_context):
        if accepted:
            return True, reason, ""
    return False, "", _rejection_reason(score, match_context)


def _match_context(
    query: str,
    candidate: dict[str, Any],
    helpers: tuple,
) -> dict[str, Any]:
    """Return normalized candidate details used by the acceptance rules."""
    normalize_text = helpers[0]
    candidate_english_name = helpers[1]
    best_candidate_overlap = helpers[2]
    numeric_match_count = helpers[3]
    normalized_query = normalize_text(query)
    normalized_english_name = normalize_text(candidate_english_name(candidate))
    best_overlap = best_candidate_overlap(query, candidate)
    has_numeric_match = numeric_match_count(normalized_query, normalized_english_name) > 0
    return _context_values(
        normalized_query,
        normalized_english_name,
        best_overlap,
        has_numeric_match,
    )


def _context_values(
    normalized_query: str,
    normalized_english_name: str,
    best_overlap: float,
    has_numeric_match: bool,
) -> dict[str, Any]:
    """Return the normalized values stored for later acceptance checks."""
    return {
        "normalized_query": normalized_query,
        "normalized_english_name": normalized_english_name,
        "best_overlap": best_overlap,
        "has_numeric_match": has_numeric_match,
    }


def _acceptance_checks(
    score: float,
    matching_config: MatchingConfig,
    match_context: dict[str, Any],
) -> list[tuple[bool, str]]:
    """Return the ordered acceptance checks evaluated for one candidate."""
    return [
        _exact_name_check(matching_config, match_context),
        _high_overlap_check(matching_config, match_context),
        _medium_score_check(score, matching_config, match_context),
        _numeric_score_check(score, matching_config, match_context),
    ]


def _exact_name_check(
    matching_config: MatchingConfig,
    match_context: dict[str, Any],
) -> tuple[bool, str]:
    """Return the exact-name acceptance rule result."""
    normalized_query = str(match_context["normalized_query"])
    normalized_english_name = str(match_context["normalized_english_name"])
    accepted = bool(
        matching_config.exact_match_accept
        and normalized_query
        and normalized_query == normalized_english_name
    )
    return accepted, "exact_normalized_name_match"


def _high_overlap_check(
    matching_config: MatchingConfig,
    match_context: dict[str, Any],
) -> tuple[bool, str]:
    """Return the high-overlap acceptance rule result."""
    best_overlap = float(match_context["best_overlap"])
    return best_overlap >= matching_config.high_overlap_threshold, "high_token_overlap"


def _medium_score_check(
    score: float,
    matching_config: MatchingConfig,
    match_context: dict[str, Any],
) -> tuple[bool, str]:
    """Return the medium-score acceptance rule result."""
    best_overlap = float(match_context["best_overlap"])
    accepted = (
        score >= matching_config.medium_score_threshold
        and best_overlap >= matching_config.medium_overlap_threshold
    )
    return accepted, "strong_score_with_good_overlap"


def _numeric_score_check(
    score: float,
    matching_config: MatchingConfig,
    match_context: dict[str, Any],
) -> tuple[bool, str]:
    """Return the numeric-score acceptance rule result."""
    best_overlap = float(match_context["best_overlap"])
    has_numeric_match = bool(match_context["has_numeric_match"])
    accepted = (
        score >= matching_config.numeric_score_threshold
        and has_numeric_match
        and best_overlap >= matching_config.numeric_overlap_threshold
    )
    return accepted, "strong_score_with_numeric_match"


def _rejection_reason(score: float, match_context: dict[str, Any]) -> str:
    """Return the detailed rejection reason for one candidate."""
    normalized_query = str(match_context["normalized_query"])
    normalized_english_name = str(match_context["normalized_english_name"])
    best_overlap = float(match_context["best_overlap"])
    has_numeric_match = bool(match_context["has_numeric_match"])
    return (
        f"Rejected: overlap={best_overlap:.3f}, score={score:.3f}, "
        f"numeric_match={has_numeric_match}, "
        "exact_name="
        f"{bool(normalized_query and normalized_query == normalized_english_name)}"
    )
