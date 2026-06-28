"""Token-based scoring logic for product matching."""

from typing import Any, Iterable

from .product_matching_helpers import _NUMERIC_PART_RE
from .product_matching_normalization import _normalized_tokens


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
