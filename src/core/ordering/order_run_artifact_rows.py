"""Structured rows for order item summary artifacts."""

from __future__ import annotations

from ..identity.manufacturer_identity import (
    extract_manufacturer_from_candidate,
    extract_manufacturer_from_name,
    manufacturer_conflict,
)

# Constants
REVIEWABLE_STATUSES = {
    "no-results", "matched-but-unavailable", "not-orderable", "manual-review-required",
    "manufacturer-mismatch",
}
SUMMARY_TIMING_KEYS = (
    "api_context_init_seconds",
    "api_search_seconds",
    "dom_wait_seconds",
    "dialog_close_seconds",
    "manual_review_lookup_seconds",
    "match_decision_seconds",
    "add_to_cart_seconds",
    "artifact_write_seconds",
    "summary_build_seconds",
)

# Helper functions
def _extract_diagnostic_and_match(status, match, decision, blocked_candidate, outcome):
    """Extract best diagnostic and match source for not-orderable items."""
    best_diagnostic = None
    match_source = match.data if match else {}
    
    if status in ("not-orderable", "matched-but-unavailable") and not match:
        best_diagnostic = _find_best_diagnostic(decision)
        if best_diagnostic and getattr(best_diagnostic, "candidate", None):
            if not blocked_candidate:
                blocked_candidate = best_diagnostic.candidate
        match_source, best_diagnostic = _resolve_match_source(
            decision, best_diagnostic, match_source
        )
    
    if not match and not match_source:
        from .order_blocked_candidate import missing_store_product_id_outcome
        if missing_store_product_id_outcome(outcome):
            match_source = blocked_candidate
    
    return best_diagnostic, match_source, blocked_candidate


def _find_best_diagnostic(decision):
    """Find the best diagnostic from decision."""
    if not decision or not getattr(decision, "diagnostics", None):
        return None
    return max(decision.diagnostics, key=lambda d: d.score, default=None)


def _resolve_match_source(decision, best_diagnostic, match_source):
    """Find match_source for orderable-missing diagnostics."""
    if not decision or not getattr(decision, "diagnostics", None):
        return match_source, best_diagnostic
        
    orderable_missing_diag = next(
        (
            d for d in decision.diagnostics
            if getattr(d, "rejection_reason", "") ==
            "Candidate missing orderable storeProductId"
        ),
        None
    )
    
    if orderable_missing_diag:
        match_source = orderable_missing_diag.candidate
        best_diagnostic = orderable_missing_diag
    
    return match_source, best_diagnostic


def _extract_query_and_score(match, blocked_candidate, outcome, best_diagnostic):
    """Extract matched query and deterministic score."""
    matched_query = match.query if match else blocked_candidate_query(outcome)
    if not matched_query and best_diagnostic:
        matched_query = best_diagnostic.query
        
    det_score = round(match.score, 6) if match else ""
    if not det_score and best_diagnostic:
        det_score = round(best_diagnostic.score, 6)
    
    return matched_query, det_score


def _basic_item_fields(item, summary, status, matched_query, det_score):
    """Extract basic item fields."""
    return {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "status": status,
        "reason": summary.reason,
        "ordered_total_qty": getattr(summary, "ordered_total_qty", ""),
        "matched_query": matched_query,
        "deterministic_score": det_score,
    }


def _timing_fields(summary):
    """Extract timing fields from summary."""
    return {
        "elapsed_seconds": round(float(getattr(summary, "elapsed_seconds", 0.0)), 3),
        "match_elapsed_seconds": round(
            float(getattr(summary, "match_elapsed_seconds", 0.0)), 3
        ),
        **_summary_timing_fields(summary),
    }


def _summary_timing_fields(summary) -> dict[str, float]:
    timings = getattr(summary, "timing_seconds", None) or {}
    return {
        key: round(float(timings.get(key, 0.0)), 3)
        for key in SUMMARY_TIMING_KEYS
    }


def _manufacturer_diagnostic_fields(
    matched_query: str, match_source: dict, decision, config=None
) -> dict[str, object]:
    """Extract manufacturer diagnostic fields for artifacts."""
    query_company = _extract_query_manufacturer(matched_query)
    candidate_company = _extract_candidate_manufacturer(match_source)
    check_decision = _compute_manufacturer_decision(
        query_company, candidate_company, config
    )
    
    return {
        "query_manufacturer": query_company or "",
        "candidate_manufacturer": candidate_company or "",
        "manufacturer_check_decision": check_decision,
    }


def _extract_query_manufacturer(matched_query: str) -> str | None:
    """Extract manufacturer from the matched query string."""
    return extract_manufacturer_from_name(matched_query) if matched_query else ""


def _extract_candidate_manufacturer(match_source: dict) -> str | None:
    """Extract manufacturer from the candidate source."""
    if not match_source:
        return ""
    candidate_name = match_source.get("productNameEn", "")
    return extract_manufacturer_from_candidate(
        candidate_name,
        match_source.get("companyName"),
        match_source.get("supplierName"),
    ) or ""


def _compute_manufacturer_decision(
    query_company: str, candidate_company: str, config
) -> str:
    """Compute manufacturer check decision (match/conflict/unknown)."""
    if not query_company or not candidate_company:
        return "unknown"
    
    threshold = getattr(config, "manufacturer_match_threshold", 0.85) if config else 0.85
    if manufacturer_conflict(query_company, candidate_company, threshold):
        return "conflict"
    return "match"


def _manual_review_reason_code(summary_status: str, outcome) -> str:
    status = getattr(outcome, "status", "") if outcome is not None else ""
    return status or summary_status


def _final_action(summary_status: str, manual_review: bool) -> str:
    return "manual_review" if manual_review else summary_status


def _final_actionable_match(item, summary_status: str, outcome, match, config=None) -> bool:
    return bool(match) and not manual_review_required(item, summary_status, outcome, config)


def text_block(title: str, row: dict[str, object]) -> str:
    """Return one readable text block for a structured artifact row."""
    body = "\n".join(f"{key}={value}" for key, value in row.items())
    return f"\n--- {title} ---\n{body}\n"


def blocked_candidate_query(outcome):
    """Return blocked candidate query from outcome."""
    from .order_blocked_candidate import blocked_candidate_query as _query
    return _query(outcome) if outcome else ""


# Main entry functions
def order_item_summary_row(item, summary, decision, outcome, config=None) -> dict[str, object]:
    """Return one compact row describing the final item outcome."""
    from .order_blocked_candidate import blocked_ai_candidate
    
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
    from .order_blocked_candidate import blocked_candidate_fields
    from .order_summary_ai_fields import summary_ai_fields
    from .order_winner_fields import candidate_summary_fields
    from ..manual_review.manual_review_reason import manual_review_reason_fields
    
    return {
        **_basic_item_fields(item, summary, status, matched_query, det_score),
        **_match_state_fields(item, status, outcome, match, config),
        **candidate_summary_fields(match_source, decision, match, summary=summary),
        **blocked_candidate_fields(blocked_candidate),
        **summary_ai_fields(outcome, manual_review, _final_action(status, manual_review)),
        **manual_review_reason_fields(status, summary.reason, outcome),
        **_manufacturer_diagnostic_fields(matched_query, match_source, decision, config),
        **_timing_fields(summary),
    }


def effective_order_status(summary_status, outcome):
    """Return effective order status considering AI outcome."""
    from .order_blocked_candidate import effective_order_status as _status
    return _status(summary_status, outcome)


# Manual review logic
def manual_review_required(item, summary_status: str, outcome, config=None) -> bool:
    """Return whether this final item state needs human review."""
    from ..manual_review.manual_review_runtime import saved_manual_review_decision
    
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


# Match state logic
def _match_state_fields(
    item, summary_status: str, outcome, match, config=None
) -> dict[str, object]:
    return {
        "matched": _final_actionable_match(
            item, summary_status, outcome, match, config
        ),
        "deterministic_match_found": bool(match),
        "manual_review_blocked_match": (
            bool(match) and
            manual_review_required(item, summary_status, outcome, config)
        ),
    }


def _final_actionable_match(item, summary_status: str, outcome, match, config=None) -> bool:
    return bool(match) and not manual_review_required(item, summary_status, outcome, config)


# Public exports
__all__ = [
    "order_item_summary_row",
    "manual_review_required",
    "manual_review_row",
    "text_block",
    "REVIEWABLE_STATUSES",
    "SUMMARY_TIMING_KEYS",
]
