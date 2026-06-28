"""Main entry functions for order item summary artifacts."""

from .order_blocked_candidate import (
    blocked_candidate_fields,
    effective_order_status,
)
from .order_summary_ai_fields import summary_ai_fields
from .order_winner_fields import candidate_summary_fields
from .order_run_artifact_rows_constants import REVIEWABLE_STATUSES
from .order_run_artifact_rows_helpers import (
    _extract_diagnostic_and_match,
    _extract_query_and_score,
    _basic_item_fields,
    _timing_fields,
    _manual_review_reason_code,
    _final_action,
)
from .manual_review_reason import manual_review_reason_fields
from .order_run_artifact_rows_match_state import _match_state_fields


def order_item_summary_row(item, summary, decision, outcome, config=None) -> dict[str, object]:
    """Return one compact row describing the final item outcome."""
    from .order_blocked_candidate import blocked_ai_candidate
    from .order_run_artifact_rows_manual_review import manual_review_required
    
    match = decision.best_match if decision else None
    blocked_candidate = blocked_ai_candidate(outcome) if not match else {}
    status = effective_order_status(summary.status, outcome)
    
    best_diagnostic, match_source, blocked_candidate = _extract_diagnostic_and_match(
        status, match, decision, blocked_candidate, outcome
    )
    manual_review = manual_review_required(item, status, outcome, config)
    matched_query, det_score = _extract_query_and_score(
        match, blocked_candidate, outcome, best_diagnostic
    )
    
    return _build_summary_row(
        item, summary, status, matched_query, det_score, 
        outcome, match, match_source, blocked_candidate, 
        decision, manual_review, config
    )


def _build_summary_row(
    item, summary, status, matched_query, det_score, 
    outcome, match, match_source, blocked_candidate, 
    decision, manual_review, config
):
    """Build the final summary row dictionary."""
    return {
        **_basic_item_fields(item, summary, status, matched_query, det_score),
        **_match_state_fields(item, status, outcome, match, config),
        **candidate_summary_fields(match_source, decision, match, summary=summary),
        **blocked_candidate_fields(blocked_candidate),
        **summary_ai_fields(outcome, manual_review, _final_action(status, manual_review)),
        **manual_review_reason_fields(status, summary.reason, outcome),
        **_timing_fields(summary),
    }
