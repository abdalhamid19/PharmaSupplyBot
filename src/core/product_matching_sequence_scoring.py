"""Sequence-based scoring logic for product matching."""

from difflib import SequenceMatcher
from typing import Any, Iterable

from .product_matching_normalization import _normalize_text
from .product_matching_token_scoring import _candidate_english_name


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
    from .product_matching_token_scoring import _token_overlap_score
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
