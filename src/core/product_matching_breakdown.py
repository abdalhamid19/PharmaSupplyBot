"""Score breakdown computation for product matching."""

from typing import Any

from .candidate_identity import candidate_store_product_id
from .config.config_models import MatchingConfig
from .matching_models import MatchScoreBreakdown
from .matching_penalties import penalty_breakdown
from .product_matching_normalization import _normalize_text
from .product_matching_sequence_scoring import (
    _candidate_texts,
    _best_sequence_score,
    _best_overlap_score,
    _exact_or_contained_bonus,
    _availability_bonus,
)
from .product_matching_token_scoring import (
    _numeric_overlap_score,
    _candidate_english_name,
    _token_overlap_score,
    _numeric_match_count,
)


def _empty_breakdown() -> MatchScoreBreakdown:
    """Return a zero-score breakdown when no candidate text is available."""
    return MatchScoreBreakdown(
        sequence_score=0.0,
        overlap_score=0.0,
        numeric_overlap=0.0,
        exact_bonus=0.0,
        availability_bonus=0.0,
        critical_penalty=0.0,
        extra_token_penalty=0.0,
        semantic_penalty=0.0,
        total_score=0.0,
    )


def _scored_breakdown(
    query: str,
    candidate: dict[str, Any],
    candidate_texts: list[str],
    matching_config: MatchingConfig,
) -> MatchScoreBreakdown:
    """Compute full score breakdown with all component scoring logic."""
    normalized_query = _normalize_text(query)
    return _breakdown_from_components(
        _best_sequence_score(normalized_query, candidate_texts),
        _best_overlap_score(normalized_query, candidate_texts),
        _numeric_overlap_score(normalized_query, candidate_texts),
        _exact_or_contained_bonus(normalized_query, candidate_texts),
        _availability_bonus(candidate),
        _lexical_penalties(query, candidate, matching_config),
    )


def _breakdown_from_components(
    sequence_score: float,
    overlap_score: float,
    numeric_overlap_score: float,
    exact_or_contained_bonus: float,
    availability_bonus: float,
    lexical_penalty: float,
) -> MatchScoreBreakdown:
    """Build a breakdown and compute the total score from all components."""
    total_score = _total_score(
        _score_components(
            sequence_score,
            overlap_score,
            numeric_overlap_score,
            exact_or_contained_bonus,
            availability_bonus,
        ),
        lexical_penalty,
    )
    return MatchScoreBreakdown(
        sequence_score=sequence_score,
        overlap_score=overlap_score,
        numeric_overlap=numeric_overlap_score,
        exact_bonus=exact_or_contained_bonus,
        availability_bonus=availability_bonus,
        critical_penalty=0.0,
        extra_token_penalty=0.0,
        semantic_penalty=lexical_penalty,
        total_score=total_score,
    )


def _score_components(
    sequence_score: float,
    overlap_score: float,
    numeric_overlap_score: float,
    exact_or_contained_bonus: float,
    availability_bonus: float,
) -> float:
    """Sum all positive scoring components before applying penalties."""
    return (
        (sequence_score * 5.0)
        + (overlap_score * 10.0)
        + (numeric_overlap_score * 5.0)
        + exact_or_contained_bonus
        + availability_bonus
    )


def _lexical_penalties(
    query: str, candidate: dict[str, Any], matching_config: MatchingConfig
) -> float:
    """Compute lexical penalty from matching rules."""
    penalties = penalty_breakdown(
        query,
        _candidate_english_name(candidate),
        matching_config.critical_token_penalty,
        matching_config.distinguishing_token_penalty,
        matching_config.semantic_mismatch_penalty,
    )
    return sum(penalties.values())


def _total_score(pre_penalty_score: float, lexical_penalty: float) -> float:
    """Apply lexical penalties, clamping result to a minimum of zero."""
    return max(0.0, pre_penalty_score + lexical_penalty)
