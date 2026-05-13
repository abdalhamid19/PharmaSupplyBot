"""Configuration models for component-aware drug matching."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchingConfig:
    """Thresholds used by the indexed drug matcher."""

    fuzzy_threshold: int = 80
    brand_prefix_min: int = 4
    brand_prefix_ratio: float = 0.75
    ai_verify_threshold: float = 90.0
    ai_batch_size: int = 20
    ai_max_concurrent: int = 5
    top_k_candidates: int = 10
    ai_review_threshold: float = 0.8
    ai_search_limit: int | None = None
    ai_verify_policy: str = "score"
    ai_verify_limit: int | None = None
    ai_search_policy: str = "review-candidates"
    ai_search_min_candidate_score: float = 80.0
    ai_search_accept_confidence: float = 0.75
    ai_search_candidate_limit: int = 5
    ai_search_review_candidate_min_score: float = 68.0
    ai_search_review_candidate_limit: int = 8
    ai_search_review_accept_confidence: float = 0.85
    ai_search_allow_component_mismatch_reasons: tuple[str, ...] = (
        "different_brand",
        "brand_prefix_mismatch",
        "different_import_status",
        "different_modifier",
        "different_quantity",
        "different_volume",
    )
