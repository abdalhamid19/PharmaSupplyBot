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
    """Return a saved manual-review decision without creating a new DB file."""
    if not DEFAULT_MANUAL_REVIEW_DB.exists():
        return None
    return ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup(item.code, item.name)


def manual_review_queries(item: Item, base_queries: list[str]) -> list[str]:
    """Prepend saved corrected queries to the normal Tawreed search queries."""
    decision = saved_manual_review_decision(item)
    preferred = _preferred_query(decision)
    if not preferred:
        return base_queries
    return [preferred, *[query for query in base_queries if query != preferred]]


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
    """Return a forced approved match when a saved storeProductId appears."""
    decision = saved_manual_review_decision(item)
    if not decision or not decision.approved or not decision.correct_store_product_id:
        return None
    target_id = decision.correct_store_product_id
    for query, candidates in results:
        for index, candidate in enumerate(candidates):
            if candidate_store_product_id(candidate) == target_id:
                match = SearchMatch(query, index, 999.0, candidate)
                return MatchDecision(match, [], "Approved by saved manual review.")
    return None


def _blocks_candidate(decision: ManualReviewDecision | None) -> bool:
    return bool(
        decision
        and decision.manual_decision == "not_matching"
        and decision.correct_store_product_id
    )


def _preferred_query(decision: ManualReviewDecision | None) -> str:
    if not decision:
        return ""
    return decision.correct_query or decision.correct_product_name or ""
