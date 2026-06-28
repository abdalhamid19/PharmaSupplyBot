"""Score API functions for product matching."""

from typing import Any

from .candidate_identity import candidate_store_product_id
from .config.config_models import MatchingConfig
from .matching_models import MatchScoreBreakdown
from .product_matching_normalization import _normalize_text
from .product_matching_sequence_scoring import _candidate_texts
from .product_matching_token_scoring import (
    _candidate_english_name,
    _token_overlap_score,
    _numeric_match_count,
)
from .product_matching_breakdown import _empty_breakdown, _scored_breakdown


def _match_score(query: str, candidate: dict[str, Any]) -> float:
    """Score a Tawreed search result against the requested Excel item text."""
    from .matching_rules import default_matching_config

    return _match_score_breakdown_for_config(
        query, candidate, default_matching_config()
    ).total_score


def _match_score_breakdown_for_config(
    query: str, candidate: dict[str, Any], matching_config: MatchingConfig
) -> MatchScoreBreakdown:
    """Return a score breakdown using the requested matching configuration."""
    candidate_texts = _candidate_texts(candidate)
    if not candidate_texts:
        return _empty_breakdown()
    return _scored_breakdown(query, candidate, candidate_texts, matching_config)


def _match_sort_key(
    query: str,
    candidate: dict[str, Any],
    score: float,
) -> tuple[float, int, float, int, int, int, float, float, str]:
    """Build a stable sort key for choosing the best search match."""
    normalized_query = _normalize_text(query)
    normalized_english_name = _normalize_text(_candidate_english_name(candidate))
    return (
        score,
        int(normalized_query == normalized_english_name),
        _token_overlap_score(query, _candidate_english_name(candidate)),
        _numeric_match_count(normalized_query, normalized_english_name),
        int(candidate.get("availableQuantity") or 0),
        int(candidate.get("productsCount") or 0),
        float(candidate.get("discountPercent") or 0.0),
        -float(candidate.get("salePrice") or 0.0),
        candidate_store_product_id(candidate),
    )
