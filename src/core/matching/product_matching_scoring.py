"""Scoring functions for product matching — consolidated."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Iterable

from .candidate_identity import candidate_store_product_id
from ..config.config_models import MatchingConfig
from ..matching_types import MatchScoreBreakdown
from .matching_penalties import penalty_breakdown
from .product_matching_helpers import (
    _NUMERIC_PART_RE,
    _normalize_text,
    _normalized_tokens,
)


# ── Token-based scoring (merged from product_matching_token_scoring.py) ──


def _token_overlap_score(query: str, candidate: str) -> float:
    """Measure how much the candidate tokens overlap the query tokens."""
    query_tokens = _normalized_tokens(query)
    candidate_tokens = _normalized_tokens(candidate)
    if not query_tokens or not candidate_tokens:
        return 0.0
    total_score = sum(
        _best_token_score(qt, candidate_tokens) for qt in query_tokens
    )
    return total_score / len(query_tokens)


def _best_token_score(query_token: str, candidate_tokens: list[str]) -> float:
    """Return the best overlap score for one query token."""
    best_score = 0.0
    for candidate_token in candidate_tokens:
        if query_token == candidate_token:
            return 1.0
        if query_token in candidate_token or candidate_token in query_token:
            best_score = max(best_score, 0.7)
    return best_score


def _numeric_overlap_score(
    normalized_query: str, candidate_texts: Iterable[str]
) -> float:
    """Return how well numeric tokens in the query appear in candidate names."""
    query_numeric_tokens = _numeric_tokens(normalized_query)
    if not query_numeric_tokens:
        return 0.0
    numeric_scores = [
        _numeric_overlap_ratio(query_numeric_tokens, _numeric_tokens(candidate_text))
        for candidate_text in candidate_texts
    ]
    return max(numeric_scores, default=0.0)


def _numeric_tokens(text: str) -> set[str]:
    """Return tokens that contain at least one digit."""
    return {
        numeric_part
        for token in text.split()
        for numeric_part in _NUMERIC_PART_RE.findall(token)
    }


def _numeric_overlap_ratio(
    query_numeric_tokens: set[str],
    candidate_numeric_tokens: set[str],
) -> float:
    """Return the fraction of query numeric tokens found in the candidate."""
    return len(query_numeric_tokens & candidate_numeric_tokens) / max(
        1, len(query_numeric_tokens)
    )


def _numeric_match_count(normalized_query: str, normalized_name: str) -> int:
    """Return how many numeric tokens the query and candidate share."""
    return len(_numeric_tokens(normalized_query) & _numeric_tokens(normalized_name))


def _best_candidate_overlap(query: str, candidate: dict[str, Any]) -> float:
    """Return the best overlap score across English and Arabic names."""
    return max(
        _token_overlap_score(query, _candidate_english_name(candidate)),
        _token_overlap_score(query, str(candidate.get("productName") or "")),
    )


def _candidate_english_name(candidate: dict[str, Any]) -> str:
    """Return the raw English candidate name used for matching."""
    return str(
        candidate.get("productNameEn") or candidate.get("productNameEnFallback") or ""
    )


# ── Sequence-based scoring (merged from product_matching_sequence_scoring.py) ──


def _candidate_texts(candidate: dict[str, Any]) -> list[str]:
    """Return normalized English and Arabic candidate names."""
    english_name = _normalize_text(_candidate_english_name(candidate))
    arabic_name = _normalize_text(str(candidate.get("productName") or ""))
    return [text for text in (english_name, arabic_name) if text]


def _best_sequence_score(
    normalized_query: str, candidate_texts: Iterable[str]
) -> float:
    """Return the best sequence similarity against all candidate names."""
    return max(
        SequenceMatcher(None, normalized_query, candidate_text).ratio()
        for candidate_text in candidate_texts
    )


def _best_overlap_score(
    normalized_query: str, candidate_texts: Iterable[str]
) -> float:
    """Return the best token overlap score against all candidate names."""
    if not normalized_query:
        return 0.0
    return max(
        _token_overlap_score(normalized_query, candidate_text)
        for candidate_text in candidate_texts
    )


def _exact_or_contained_bonus(
    normalized_query: str, candidate_texts: Iterable[str]
) -> float:
    """Return the exact-match bonus when one text strongly contains the other."""
    if not normalized_query:
        return 0.0
    if any(
        normalized_query == candidate_text
        or normalized_query in candidate_text
        or candidate_text in normalized_query
        for candidate_text in candidate_texts
    ):
        return 2.0
    return 0.0


def _availability_bonus(candidate: dict[str, Any]) -> float:
    """Return a small score bonus or penalty based on availability signals."""
    available_quantity = int(candidate.get("availableQuantity") or 0)
    products_count = int(candidate.get("productsCount") or 0)
    if available_quantity > 0 or products_count > 0:
        return 1.0
    return -1.5


# ── Score breakdown (merged from product_matching_breakdown.py) ──


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


# ── Score API (merged from product_matching_score_api.py) ──


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


__all__ = [
    "_normalize_text",
    "_normalized_tokens",
    "_token_overlap_score",
    "_best_token_score",
    "_candidate_texts",
    "_candidate_english_name",
    "_best_sequence_score",
    "_best_overlap_score",
    "_numeric_overlap_score",
    "_numeric_tokens",
    "_numeric_overlap_ratio",
    "_exact_or_contained_bonus",
    "_availability_bonus",
    "_numeric_match_count",
    "_best_candidate_overlap",
    "_empty_breakdown",
    "_scored_breakdown",
    "_breakdown_from_components",
    "_score_components",
    "_lexical_penalties",
    "_total_score",
    "_match_score",
    "_match_score_breakdown_for_config",
    "_match_sort_key",
]
