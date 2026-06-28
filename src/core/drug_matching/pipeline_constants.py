"""Constants for the matching pipeline."""

from __future__ import annotations

_RESULT_COLS = [
    "code", "drug_name", "matched_product_name_en",
    "matched_product_name_ar", "matched_store_product_id",
    "match_score", "verified", "match_method", "ai_confidence", "ai_review_confidence",
]

__all__ = ["_RESULT_COLS"]
