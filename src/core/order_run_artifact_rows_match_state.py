"""Match state logic for order item summary artifacts."""


def _match_state_fields(
    item, summary_status: str, outcome, match, config=None
) -> dict[str, object]:
    from .order_run_artifact_rows_manual_review import manual_review_required
    
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
    from .order_run_artifact_rows_manual_review import manual_review_required
    
    return bool(match) and not manual_review_required(item, summary_status, outcome, config)
