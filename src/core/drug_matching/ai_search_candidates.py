"""Candidate gathering and validation for AI search."""

from rapidfuzz import fuzz, process

from .normalizer import components_match, parse_drug
from .ai_search_helpers import (
    _brand_similarity,
    _is_reviewable_component_mismatch,
    _review_candidates_enabled,
    _with_candidate_reason,
)


def _search_candidates(parsed, norm, index, cfg, price=None):
    """Gather fuzzy + brand candidates for unmatched search."""
    candidates = []
    limit = cfg.ai_search_candidate_limit
    for idx, score in index.get_candidates(parsed, limit=limit, price=price):
        _append_search_candidate(candidates, parsed, index, cfg, idx, score)
    for scorer in [fuzz.token_set_ratio, fuzz.token_sort_ratio]:
        results = process.extract(
            norm, index.norms,
            scorer=scorer, limit=limit,
        )
        for _, score, idx in results:
            if score >= cfg.ai_search_review_candidate_min_score:
                _append_search_candidate(candidates, parsed, index, cfg, idx, score)
    brand_hits = index.lookup_by_brand(parsed)
    for rec, idx in brand_hits:
        score = index.score_candidate(norm, idx)
        if score >= cfg.ai_search_review_candidate_min_score:
            _append_search_candidate(candidates, parsed, index, cfg, idx, score)
    return _dedupe_candidates(candidates)


def _eligible_search_candidates(parsed, candidates, index, cfg):
    """Filter candidates based on component status and policy."""
    eligible = []
    review_count = 0
    for candidate in candidates:
        rec, score, idx = candidate[:3]
        ok, reason = _candidate_component_status(candidate, parsed, index, cfg)
        if ok and score >= cfg.ai_search_min_candidate_score:
            eligible.append(candidate)
        elif (
            not ok
            and
            _review_candidates_enabled(cfg)
            and score >= cfg.ai_search_review_candidate_min_score
            and review_count < cfg.ai_search_review_candidate_limit
            and _is_reviewable_component_mismatch(parsed, index.get_parsed(idx), reason, score, cfg)
        ):
            eligible.append(_with_candidate_reason(candidate, reason))
            review_count += 1
    return eligible


def _dedupe_candidates(candidates):
    """Remove duplicate candidates by store_product_id."""
    seen = set()
    out = []
    for candidate in candidates:
        rec = candidate[0]
        sid = rec["store_product_id"]
        if sid not in seen:
            seen.add(sid)
            out.append(candidate)
    return out


def _append_search_candidate(candidates, parsed, index, cfg, idx, score):
    """Append candidate if component match is acceptable."""
    candidate = index.get_parsed(idx)
    ok, reason = components_match(
        parsed, candidate,
        cfg.brand_prefix_min,
    )
    if ok or _is_reviewable_component_mismatch(parsed, candidate, reason, score, cfg):
        candidates.append((index.get_record(idx), score, idx, reason))


def _candidate_component_status(candidate, parsed, index, cfg):
    """Check component status of a candidate."""
    reason = candidate[3] if len(candidate) > 3 else ""
    if reason:
        return reason == "ok", reason
    return components_match(
        parsed, index.get_parsed(candidate[2]),
        cfg.brand_prefix_min,
    )


def _search_acceptance_threshold(ai_result, candidates, parsed, index, cfg):
    """Determine acceptance threshold based on component status."""
    threshold = cfg.ai_search_accept_confidence
    if not ai_result or not ai_result.get("record"):
        return threshold, "no_record"
    best_index = ai_result.get("best_index", 0)
    if not isinstance(best_index, int) or best_index <= 0 or best_index > len(candidates):
        return threshold, "invalid_best_index"
    candidate = candidates[best_index - 1]
    ok, reason = _candidate_component_status(candidate, parsed, index, cfg)
    if ok:
        return threshold, "ok"
    if not _is_reviewable_component_mismatch(
        parsed, index.get_parsed(candidate[2]), reason, candidate[1], cfg,
    ):
        return max(threshold, cfg.ai_search_review_accept_confidence), "unsafe_component_mismatch"
    return max(threshold, cfg.ai_search_review_accept_confidence), reason


def _apply_search_result(results, idx, ai_result):
    """Apply AI search result to results DataFrame."""
    rec = ai_result["record"]
    results.at[idx, "matched_product_name_en"] = rec["product_name_en"]
    results.at[idx, "matched_product_name_ar"] = rec["product_name_ar"]
    results.at[idx, "matched_store_product_id"] = rec["store_product_id"]
    results.at[idx, "match_score"] = round(ai_result.get("score", 0), 1)
    results.at[idx, "verified"] = "ai_found"
    results.at[idx, "match_method"] = "ai_search"
    results.at[idx, "ai_confidence"] = round(ai_result.get("confidence", 0), 2)
    component_reason = ai_result.get("_component_reason", "")
    if component_reason and component_reason != "ok":
        results.at[idx, "_ai_component_reason"] = component_reason
    from .ai_search_helpers import _set_internal_matched_price
    _set_internal_matched_price(results, idx, rec.get("price", ""))


__all__ = [
    "_search_candidates",
    "_eligible_search_candidates",
    "_dedupe_candidates",
    "_append_search_candidate",
    "_candidate_component_status",
    "_search_acceptance_threshold",
    "_apply_search_result",
]
