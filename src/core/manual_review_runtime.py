"""Runtime helpers that apply saved manual-review decisions to matching."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterable, Iterator

from .manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)
from .manual_review_hints import hint_key
from .utils.excel import Item
from .manual_review_helpers import (
    _blocks_candidate,
    _find_manual_review_match,
    _lookup_with_retry,
    _preferred_queries,
)

_MANUAL_REVIEW_CACHE: ContextVar["ManualReviewDecisionCache | None"] = ContextVar(
    "manual_review_decision_cache", default=None
)


class ManualReviewDecisionCache:
    """In-memory decisions cache for one order run."""

    def __init__(self, decisions: dict[tuple[str, str], ManualReviewDecision]):
        self._decisions = decisions

    def lookup(self, item: Item) -> ManualReviewDecision | None:
        """Return one cached decision by normalized item key."""
        return self._decisions.get(hint_key(item.code, item.name))


def preload_manual_review_decisions(items: Iterable[Item]) -> ManualReviewDecisionCache:
    """Load manual-review decisions for this run in one store call."""
    decisions = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup_many(items)
    return ManualReviewDecisionCache(decisions)


@contextmanager
def manual_review_cache_context(
    cache: ManualReviewDecisionCache | None,
) -> Iterator[None]:
    """Activate a manual-review decisions cache for matching helpers."""
    if cache is None:
        yield
        return
    token = _MANUAL_REVIEW_CACHE.set(cache)
    try:
        yield
    finally:
        _MANUAL_REVIEW_CACHE.reset(token)


def saved_manual_review_decision(item: Item) -> ManualReviewDecision | None:
    """Return a saved manual-review decision with retry logic."""
    cache = _MANUAL_REVIEW_CACHE.get()
    if cache is not None:
        return cache.lookup(item)
    
    return _lookup_with_retry(item)


def manual_review_queries(
    item: Item, base_queries: list[str], decision: ManualReviewDecision | None = None
) -> list[str]:
    """Prepend saved corrected queries to the normal Tawreed search queries."""
    decision = saved_manual_review_decision(item) if decision is None else decision
    preferred = _preferred_queries(decision)
    if not preferred:
        return base_queries
        
    final_queries = [p for p in preferred if p]
    for q in base_queries:
        if q not in final_queries:
            final_queries.append(q)
    return final_queries


def filter_manual_review_candidates(
    item: Item,
    results: list[tuple[str, list[dict]]],
    decision: ManualReviewDecision | None = None,
) -> list[tuple[str, list[dict]]]:
    """Remove candidates previously rejected as not matching by a human."""
    decision = saved_manual_review_decision(item) if decision is None else decision
    if not _blocks_candidate(decision):
        return results
    from .candidate_identity import candidate_store_product_id
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
    item: Item,
    results: list[tuple[str, list[dict]]],
    decision: ManualReviewDecision | None = None,
):
    """Return a forced approved match when a saved ID or exact name appears."""
    from .matching_models import MatchDecision
    decision = saved_manual_review_decision(item) if decision is None else decision
    if not decision or not decision.approved:
        return None

    target_id = decision.correct_store_product_id
    target_en = decision.correct_product_name.lower() if decision.correct_product_name else ""
    target_ar = getattr(decision, "correct_product_name_ar", "").lower()

    if not target_id and not target_en and not target_ar:
        return None

    return _find_manual_review_match(results, target_id, target_en, target_ar)


__all__ = [
    "ManualReviewDecisionCache",
    "preload_manual_review_decisions",
    "manual_review_cache_context",
    "saved_manual_review_decision",
    "manual_review_queries",
    "filter_manual_review_candidates",
    "manual_review_match",
]
