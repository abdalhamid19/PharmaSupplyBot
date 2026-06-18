"""Order run summary, AI trace, and manual-review artifact writers."""
from __future__ import annotations

from ..core.order_ai_trace_rows import order_ai_trace_rows
from ..core.order_run_artifact_rows import (
    manual_review_required,
    manual_review_row,
    order_item_summary_row,
    text_block,
)
from ..core.utils.excel import Item
from .tawreed_artifacts import append_csv_artifact, append_text_artifact
from .tawreed_match_logs import OrderItemSummary


def append_order_ai_trace_artifacts(
    profile_key: str, item: Item, outcome, label_suffix: str | None = None
) -> None:
    """Append detailed AI trace rows to CSV and TXT artifacts."""
    rows = order_ai_trace_rows(item, outcome)
    if not rows:
        return
    append_csv_artifact(profile_key, "order_ai_trace", rows, label_suffix)
    append_text_artifact(
        profile_key, "order_ai_trace", _text_rows("ai_trace", rows), label_suffix
    )


def append_order_item_artifacts(
    profile_key: str,
    item: Item,
    summary: OrderItemSummary,
    decision,
    outcome,
    label_suffix: str | None = None,
) -> None:
    """Append one item summary row and optional manual-review row."""
    row = order_item_summary_row(item, summary, decision, outcome)
    _append_item_summary_row(profile_key, row, label_suffix)
    _append_final_trace_row(profile_key, row, label_suffix)
    requires_review = manual_review_required(item, summary.status, outcome, bot.config.matching)

    if requires_review:
        append_manual_review_artifacts(profile_key, item, summary, decision, outcome, label_suffix)
    elif bot.config.matching.enable_auto_save_verified_match:
        _auto_save_verified_match(item, decision)


def _auto_save_verified_match(item: Item, decision) -> None:
    if not decision or not decision.best_match:
        return
        
    match = decision.best_match
    if match.score == 999.0 and "Approved by saved manual review" in (decision.final_reason or ""):
        return
        
    from ..core.candidate_identity import candidate_store_product_id
    from ..core.order_ai_records import candidate_name, candidate_ar
    from ..core.manual_review_store import ManualReviewStore, ManualReviewDecision, DEFAULT_MANUAL_REVIEW_DB
    
    store_id = candidate_store_product_id(match.data)
    name_en = candidate_name(match.data)
    name_ar = candidate_ar(match.data)
    
    run = current_artifact_run()
    run_id = run.directory.name if run else ""
    
    new_decision = ManualReviewDecision(
        item_code=item.code,
        item_name=item.name,
        approved=True,
        correct_store_product_id=store_id,
        manual_decision="auto_matched",
        correct_query="",
        run_id=run_id,
        correct_product_name=name_en,
        correct_product_name_ar=name_ar
    )
    ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).upsert(new_decision)


from ..core.artifact_run import current_artifact_run
from ..core.manual_review_candidate_store import append_review_candidates
from ..core.manual_review_candidates import review_candidate_options

def append_manual_review_artifacts(
    profile_key: str,
    item: Item,
    summary: OrderItemSummary,
    decision,
    outcome,
    label_suffix: str | None = None,
) -> None:
    """Append one manual-review row to CSV and TXT artifacts, and candidates to JSONL."""
    row = manual_review_row(item, summary, decision, outcome)
    append_csv_artifact(profile_key, "manual_review", [row], label_suffix)
    append_text_artifact(
        profile_key, "manual_review", text_block("manual_review", row), label_suffix
    )
    
    run = current_artifact_run()
    if run and decision:
        # Save up to 5 candidates for the UI
        options = review_candidate_options(decision, limit=5)
        append_review_candidates(run.directory, item.code, item.name, options)


def _final_trace_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "phase": "item_final",
        "item_code": row["item_code"],
        "item_name": row["item_name"],
        "ai_status": row["ai_status"],
        "result": row["status"],
        "confidence": row["ai_confidence"],
        "model_used": row["ai_model"],
        "provider_used": row["ai_provider"],
        "reason": row["reason"],
        "manual_review_required": row["manual_review_required"],
        "manual_review_category": row.get("manual_review_category", ""),
        "manual_review_reason_detail": row.get("manual_review_reason_detail", ""),
        "manual_review_blocking_phase": row.get("manual_review_blocking_phase", ""),
        "candidate_safety_reason": row.get("candidate_safety_reason", ""),
    }


def _append_item_summary_row(
    profile_key: str, row: dict[str, object], label_suffix: str | None
) -> None:
    append_csv_artifact(profile_key, "order_item_summary", [row], label_suffix)
    append_text_artifact(
        profile_key, "order_item_summary", text_block("item", row), label_suffix
    )


def _append_final_trace_row(
    profile_key: str, row: dict[str, object], label_suffix: str | None
) -> None:
    final_row = _final_trace_row(row)
    append_csv_artifact(profile_key, "order_ai_trace", [final_row], label_suffix)
    append_text_artifact(
        profile_key, "order_ai_trace", text_block("item_final", final_row), label_suffix
    )


def _text_rows(title: str, rows: list[dict[str, object]]) -> str:
    return "".join(text_block(title, row) for row in rows)
