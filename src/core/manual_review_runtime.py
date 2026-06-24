"""Runtime helpers that apply saved manual-review decisions to matching."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterable, Iterator

from .manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)
from .manual_review_hints import hint_key
from .candidate_identity import candidate_store_product_id
from .matching_models import MatchDecision, SearchMatch
from .utils.excel import Item

logger = logging.getLogger(__name__)

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
    
    # Retry up to 3 times with exponential backoff
    for attempt in range(3):
        try:
            result = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup(item.code, item.name)
            if attempt > 0:
                logger.info(f"Manual review lookup succeeded on attempt {attempt + 1} for {item.code}/{item.name}")
            return result
        except Exception as e:
            if attempt < 2:
                logger.warning(
                    f"Manual review lookup attempt {attempt + 1} failed for {item.code}/{item.name}: "
                    f"{type(e).__name__}: {e}, retrying..."
                )
                time.sleep(0.05 * (attempt + 1))
            else:
                logger.error(
                    f"Manual review lookup failed after 3 attempts for {item.code}/{item.name}: "
                    f"{type(e).__name__}: {e}"
                )
                return None


def manual_review_queries(
    item: Item,
    base_queries: list[str],
    decision: ManualReviewDecision | None = None,
) -> list[str]:
    """Prepend saved corrected queries to the normal Tawreed search queries."""
    decision = saved_manual_review_decision(item) if decision is None else decision
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
    item: Item,
    results: list[tuple[str, list[dict]]],
    decision: ManualReviewDecision | None = None,
) -> list[tuple[str, list[dict]]]:
    """Remove candidates previously rejected as not matching by a human."""
    decision = saved_manual_review_decision(item) if decision is None else decision
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
    item: Item,
    results: list[tuple[str, list[dict]]],
    decision: ManualReviewDecision | None = None,
) -> MatchDecision | None:
    """Return a forced approved match when a saved ID or exact name appears."""
    decision = saved_manual_review_decision(item) if decision is None else decision
    if not decision or not decision.approved:
        return None

    target_id = decision.correct_store_product_id
    target_en = decision.correct_product_name.lower() if decision.correct_product_name else ""
    target_ar = getattr(decision, "correct_product_name_ar", "").lower()

    if not target_id and not target_en and not target_ar:
        return None

    if target_id:
        id_match = _manual_review_id_match(results, target_id)
        if id_match is not None:
            return id_match

    # Fallback: honour the saved correction by exact name even when the saved
    # store id is missing from the results (e.g. the product was re-listed under
    # a new orderable id or offered by a different store).
    return _manual_review_name_match(results, target_en, target_ar)


def _manual_review_id_match(
    results: list[tuple[str, list[dict]]],
    target_id: str,
) -> MatchDecision | None:
    """Force a match when a candidate exposes the saved orderable store id."""
    from .candidate_identity import candidate_store_product_id

    for query, candidates in results:
        for index, candidate in enumerate(candidates):
            if candidate_store_product_id(candidate) == target_id:
                match = SearchMatch(query, index, 999.0, candidate)
                return MatchDecision(match, [], "Approved by saved manual review (ID match).")
    return None


def _manual_review_name_match(
    results: list[tuple[str, list[dict]]],
    target_en: str,
    target_ar: str,
) -> MatchDecision | None:
    """Force a match when an orderable candidate exactly matches the saved name."""
    if not target_en and not target_ar:
        return None
    from .order_ai_records import candidate_name, candidate_ar
    from .candidate_identity import candidate_store_product_id

    for query, candidates in results:
        for index, candidate in enumerate(candidates):
            if not candidate_store_product_id(candidate):
                continue
            c_en = candidate_name(candidate).lower()
            c_ar = candidate_ar(candidate).lower()
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
