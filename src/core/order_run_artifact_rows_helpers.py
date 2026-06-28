"""Helper functions for order run artifact rows."""

from __future__ import annotations

from .order_blocked_candidate import blocked_ai_candidate, blocked_candidate_query
from .order_run_artifact_rows_constants import REVIEWABLE_STATUSES, SUMMARY_TIMING_KEYS


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


def _manual_review_reason_code(summary_status: str, outcome) -> str:
    status = getattr(outcome, "status", "") if outcome is not None else ""
    return status or summary_status


def _final_action(summary_status: str, manual_review: bool) -> str:
    return "manual_review" if manual_review else summary_status


def _final_actionable_match(item, summary_status: str, outcome, match, config=None) -> bool:
    from .order_run_artifact_rows import manual_review_required
    return bool(match) and not manual_review_required(item, summary_status, outcome, config)


def text_block(title: str, row: dict[str, object]) -> str:
    """Return one readable text block for a structured artifact row."""
    body = "\n".join(f"{key}={value}" for key, value in row.items())
    return f"\n--- {title} ---\n{body}\n"
