"""Helper functions for manual review runtime."""

import logging
import time

from .manual_review_store import ManualReviewDecision
from .utils.excel import Item

logger = logging.getLogger(__name__)


def _lookup_with_retry(item: Item, max_attempts: int = 3) -> ManualReviewDecision | None:
    """Lookup decision with retry logic."""
    from .manual_review_store import DEFAULT_MANUAL_REVIEW_DB
    for attempt in range(max_attempts):
        try:
            result = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup(item.code, item.name)
            if attempt > 0:
                logger.info(f"Manual review lookup succeeded on attempt {attempt + 1} for {item.code}/{item.name}")
            return result
        except Exception as e:
            if attempt < max_attempts - 1:
                _log_retry_warning(item, attempt, e)
                time.sleep(0.05 * (attempt + 1))
            else:
                _log_retry_failure(item, max_attempts, e)
                return None


def _log_retry_warning(item, attempt, e):
    """Log retry warning."""
    logger.warning(f"Manual review lookup attempt {attempt + 1} failed for {item.code}/{item.name}: {type(e).__name__}: {e}, retrying...")


def _log_retry_failure(item, max_attempts, e):
    """Log retry failure."""
    logger.error(f"Manual review lookup failed after {max_attempts} attempts for {item.code}/{item.name}: {type(e).__name__}: {e}")


def _blocks_candidate(decision: ManualReviewDecision | None) -> bool:
    """Check if decision blocks candidate."""
    return bool(
        decision
        and decision.manual_decision == "not_matching"
        and decision.correct_store_product_id
    )


def _preferred_queries(decision: ManualReviewDecision | None) -> list[str]:
    """Extract preferred queries from decision."""
    if not decision:
        return []
    if decision.correct_query:
        return [decision.correct_query]
    return [decision.correct_product_name, getattr(decision, "correct_product_name_ar", "")]


def _find_manual_review_match(results, target_id, target_en, target_ar):
    """Find match by ID or name."""
    if target_id:
        id_match = _manual_review_id_match(results, target_id)
        if id_match is not None:
            return id_match
    return _manual_review_name_match(results, target_en, target_ar)


def _manual_review_id_match(
    results: list[tuple[str, list[dict]]],
    target_id: str,
):
    """Force a match when a candidate exposes the saved orderable store id."""
    from .candidate_identity import candidate_store_product_id
    from .matching_models import SearchMatch, MatchDecision

    for query, candidates in results:
        for index, candidate in enumerate(candidates):
            if candidate_store_product_id(candidate) == target_id:
                match = SearchMatch(query, index, 999.0, candidate)
                return MatchDecision(match, [], "Approved by saved manual review (ID match).")
    return None


def _manual_review_name_match(
    results: list[tuple[str, list[dict]]], target_en: str, target_ar: str
):
    """Force a match when an orderable candidate exactly matches the saved name."""
    if not target_en and not target_ar:
        return None
    
    for query, candidates in results:
        match = _find_name_match_in_candidates(candidates, target_en, target_ar, query)
        if match:
            return match
    return None


def _find_name_match_in_candidates(candidates, target_en, target_ar, query):
    """Find name match within candidates list."""
    from .order_ai_records import candidate_name, candidate_ar
    from .candidate_identity import candidate_store_product_id
    from .matching_models import SearchMatch, MatchDecision
    
    for index, candidate in enumerate(candidates):
        if not candidate_store_product_id(candidate):
            continue
        c_en = candidate_name(candidate).lower()
        c_ar = candidate_ar(candidate).lower()
        if (target_en and c_en == target_en) or (target_ar and c_ar == target_ar):
            match = SearchMatch(query, index, 999.0, candidate)
            return MatchDecision(match, [], "Approved by saved manual review (Name match).")
    return None


__all__ = [
    "_lookup_with_retry",
    "_log_retry_warning",
    "_log_retry_failure",
    "_blocks_candidate",
    "_preferred_queries",
    "_find_manual_review_match",
    "_manual_review_id_match",
    "_manual_review_name_match",
    "_find_name_match_in_candidates",
]
