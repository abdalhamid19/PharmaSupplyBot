"""Pure functions to translate UI selections into manual review decisions."""

from __future__ import annotations

from .manual_review_candidates import ReviewCandidateOption
from .manual_review_store import ManualReviewDecision
from .utils.excel import Item


def decision_from_selection(
    item: Item,
    selected_option: ReviewCandidateOption | None,
    not_matching: bool,
    free_text_query: str,
    run_id: str,
) -> ManualReviewDecision:
    """Return a storable decision based on human feedback."""
    if not_matching:
        return _create_not_matching(item, run_id)
    if free_text_query.strip():
        return _create_needs_correction(item, free_text_query.strip(), run_id)
    if selected_option:
        return _create_approved(item, selected_option, run_id)
    return _create_not_matching(item, run_id)


def _create_not_matching(item: Item, run_id: str) -> ManualReviewDecision:
    return ManualReviewDecision(
        item_code=item.code, item_name=item.name, approved=False,
        run_id=run_id, manual_decision="not_matching",
    )


def _create_needs_correction(item: Item, query: str, run_id: str) -> ManualReviewDecision:
    return ManualReviewDecision(
        item_code=item.code, item_name=item.name, approved=False,
        correct_query=query, run_id=run_id, manual_decision="needs_correction",
    )


def _create_approved(
    item: Item, option: ReviewCandidateOption, run_id: str
) -> ManualReviewDecision:
    return ManualReviewDecision(
        item_code=item.code, item_name=item.name, approved=True,
        correct_store_product_id=option.store_product_id,
        correct_product_name=option.name_en or "",
        correct_product_name_ar=option.name_ar or "",
        run_id=run_id, manual_decision="approved_match",
    )
