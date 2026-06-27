"""Helper functions for AI search."""

import re
from rapidfuzz import fuzz

_DANGEROUS_REVIEW_REASONS = frozenset((
    "different_age_group",
    "different_form",
    "different_route",
    "different_weight",
    "different_flavor",
    "different_product_class",
))


def _internal_value(results, idx, col: str, default=""):
    """Get internal value from results DataFrame."""
    return results.at[idx, col] if col in results.columns else default


def _set_internal_matched_price(results, idx, value):
    """Set internal matched price in results."""
    if "_matched_price" in results.columns:
        results["_matched_price"] = results["_matched_price"].astype(object)
    results.at[idx, "_matched_price"] = value


def _brand_similarity(left: str, right: str) -> float:
    """Calculate brand similarity using fuzzy matching."""
    left_clean = re.sub(r"[^A-Z0-9]", "", left)
    right_clean = re.sub(r"[^A-Z0-9]", "", right)
    if not left_clean or not right_clean:
        return 0.0
    if left_clean in right_clean or right_clean in left_clean:
        return 100.0
    return fuzz.ratio(left_clean, right_clean)


def _with_candidate_reason(candidate, reason):
    """Add reason to candidate tuple."""
    if len(candidate) > 3:
        return candidate
    return (*candidate, reason)


def _review_candidates_enabled(cfg) -> bool:
    """Check if review candidates policy is enabled."""
    return cfg.ai_search_policy in {
        "review-candidates", "expanded", "aggressive",
    }


def _is_reviewable_component_mismatch(parsed, candidate, reason, score, cfg) -> bool:
    """Check if component mismatch is reviewable."""
    if reason == "ok":
        return True
    if reason in _DANGEROUS_REVIEW_REASONS:
        return False
    if reason not in cfg.ai_search_allow_component_mismatch_reasons:
        return False
    if reason == "different_brand":
        return _brand_similarity(parsed.brand, candidate.brand) >= 80
    if reason in {"different_quantity", "different_volume"}:
        return _brand_similarity(parsed.brand, candidate.brand) >= 86
    if reason == "different_modifier" and parsed.product_class == "medicine":
        return score >= max(cfg.ai_search_review_candidate_min_score, 75)
    return True


__all__ = [
    "_internal_value",
    "_set_internal_matched_price",
    "_brand_similarity",
    "_with_candidate_reason",
    "_review_candidates_enabled",
    "_is_reviewable_component_mismatch",
]
