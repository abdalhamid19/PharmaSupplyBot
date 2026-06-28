"""Scoring functions for product matching."""

from __future__ import annotations

from typing import Any

from .product_matching_normalization import _normalize_text, _normalized_tokens
from .product_matching_token_scoring import (
    _token_overlap_score,
    _best_token_score,
    _numeric_overlap_score,
    _numeric_tokens,
    _numeric_overlap_ratio,
    _numeric_match_count,
    _best_candidate_overlap,
    _candidate_english_name,
)
from .product_matching_sequence_scoring import (
    _candidate_texts,
    _best_sequence_score,
    _best_overlap_score,
    _exact_or_contained_bonus,
    _availability_bonus,
)
from .product_matching_breakdown import (
    _empty_breakdown,
    _scored_breakdown,
    _breakdown_from_components,
    _score_components,
    _lexical_penalties,
    _total_score,
)
from .product_matching_score_api import (
    _match_score,
    _match_score_breakdown_for_config,
    _match_sort_key,
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
