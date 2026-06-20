"""Runtime helpers that apply saved manual-review decisions to matching."""

from __future__ import annotations

from .manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)
from .candidate_identity import candidate_store_product_id
from .matching_models import MatchDecision, SearchMatch
from .utils.excel import Item


def saved_manual_review_decision(item: Item) -> ManualReviewDecision | None:
    """Return a saved manual-review decision."""
    try:
        return ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup(item.code, item.name)
    except Exception:
        return None


def manual_review_queries(item: Item, base_queries: list[str]) -> list[str]:
    """Prepend saved corrected queries to the normal Tawreed search queries."""
    decision = saved_manual_review_decision(item)
    preferred = _preferred_queries(decision)
    if not preferred:
        return base_queries
        
    final_queries = []
    # Add preferred in order without duplicates
    for p in preferred:
        if p and p not in final_queries:
            final_queries.append(p)
            
    # Add base queries without duplicates
    for q in base_queries:
        if q not in final_queries:
            final_queries.append(q)
            
    return final_queries


def filter_manual_review_candidates(
    item: Item, results: list[tuple[str, list[dict]]]
) -> list[tuple[str, list[dict]]]:
    """Remove candidates previously rejected as not matching by a human."""
    decision = saved_manual_review_decision(item)
    if not _blocks_candidate(decision):
        return results
    blocked_id = decision.correct_store_product_id
    return [
        (
            query,
            [
                candidate for candidate in candidates
                if candidate_store_product_id(candidate) != blocked_id
            ],
        )
        for query, candidates in results
    ]


def manual_review_match(
    item: Item, results: list[tuple[str, list[dict]]]
) -> MatchDecision | None:
    """Return a forced approved match when a saved ID or exact name appears."""
    decision = saved_manual_review_decision(item)
    if not decision or not decision.approved:
        return None

    target_id = decision.correct_store_product_id
    target_en = decision.correct_product_name.lower() if decision.correct_product_name else ""
    target_ar = getattr(decision, "correct_product_name_ar", "").lower()

    if not target_id and not target_en and not target_ar:
        return None

    from .order_ai_records import candidate_name, candidate_ar
    from .candidate_identity import candidate_store_product_id

    for query, candidates in results:
        for index, candidate in enumerate(candidates):
            c_id = candidate_store_product_id(candidate)
            c_en = candidate_name(candidate).lower()
            c_ar = candidate_ar(candidate).lower()

            if target_id and c_id == target_id:
                match = SearchMatch(query, index, 999.0, candidate)
                return MatchDecision(match, [], "Approved by saved manual review (ID match).")
                
            if not target_id and (target_en or target_ar):
                if (target_en and c_en == target_en) or (target_ar and c_ar == target_ar):
                    match = SearchMatch(query, index, 999.0, candidate)
                    return MatchDecision(match, [], "Approved by saved manual review (Name match).")

    return None


def _blocks_candidate(decision: ManualReviewDecision | None) -> bool:
    return bool(
        decision
        and decision.manual_decision == "not_matching"
        and decision.correct_store_product_id
    )


def _preferred_queries(decision: ManualReviewDecision | None) -> list[str]:
    if not decision:
        return []
    if decision.correct_query:
        return [decision.correct_query]
    return [decision.correct_product_name, getattr(decision, "correct_product_name_ar", "")]
