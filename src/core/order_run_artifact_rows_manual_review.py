"""Manual review decision logic for order item summary artifacts."""

from .order_run_artifact_rows_constants import REVIEWABLE_STATUSES
from .order_run_artifact_rows_helpers import _manual_review_reason_code


def manual_review_required(item, summary_status: str, outcome, config=None) -> bool:
    """Return whether this final item state needs human review."""
    from .manual_review_runtime import saved_manual_review_decision
    
    decision = saved_manual_review_decision(item)
    
    if decision and decision.manual_decision == "not_matching":
        return False
    
    if decision and decision.manual_decision in ("auto_matched", "approved_match"):
        return _check_re_review_needed(decision, summary_status, config)

    if outcome is not None and outcome.manual_review:
        return True
    
    return summary_status in REVIEWABLE_STATUSES


def _check_re_review_needed(decision, summary_status, config):
    """Check if re-review is needed for saved decisions."""
    if summary_status in REVIEWABLE_STATUSES:
        re_review_key = (
            "enable_auto_match_re_review_on_fail"
            if decision.manual_decision == "auto_matched"
            else "enable_approved_match_re_review_on_fail"
        )
        if config and getattr(config, re_review_key, False):
            return True
    return False


def manual_review_row(item, summary, decision, outcome, config=None) -> dict[str, object]:
    """Return a manual-review row with empty human decision columns."""
    from .order_run_artifact_rows_main import order_item_summary_row
    
    row = order_item_summary_row(item, summary, decision, outcome, config)
    row.update(
        {
            "manual_review_reason_code": _manual_review_reason_code(row["status"], outcome),
            "manual_decision": "",
            "manual_reason": "",
            "correct_store_product_id": "",
        }
    )
    return row
