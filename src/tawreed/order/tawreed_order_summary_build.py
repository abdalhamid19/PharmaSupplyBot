"""Summary building functions for Tawreed order processing."""

from __future__ import annotations

from ...core.artifact_run import current_artifact_run
from ...core.manual_review_candidate_store import append_review_candidates
from ...core.manual_review_candidates import review_candidate_options
from ...core.manual_review_store import ManualReviewDecision, ManualReviewStore, DEFAULT_MANUAL_REVIEW_DB
from ...core.order_ai_artifacts import order_ai_trace_rows
from ...core.order_ai_matching import candidate_ar, candidate_name
from ...core.order_run_artifact_rows import manual_review_required, manual_review_row, order_item_summary_row
from ...core.utils.excel import Item
from ...core.candidate_identity import candidate_store_product_id
from ..tawreed_artifacts import append_csv_artifact, append_text_artifact
from ..tawreed_match_logs import OrderResultSummary


def append_order_ai_trace_artifacts(
    profile_key: str, item: Item, outcome, label_suffix: str | None = None
) -> None:
    """Append detailed AI trace rows to CSV and TXT artifacts."""
    from .tawreed_order_summary_format import _text_rows

    rows = order_ai_trace_rows(item, outcome)
    if not rows:
        return
    append_csv_artifact(profile_key, "order_ai_trace", rows, label_suffix)
    append_text_artifact(
        profile_key, "order_ai_trace", _text_rows("ai_trace", rows), label_suffix
    )


def append_order_item_artifacts(
    profile_key: str, item: Item, summary: OrderResultSummary, decision, outcome,
    label_suffix: str | None = None, matching_config=None
) -> None:
    """Append one item summary row and optional manual-review row."""
    from .tawreed_order_summary_format import _append_item_summary_row, _append_final_trace_row

    row = order_item_summary_row(item, summary, decision, outcome, matching_config)
    _append_item_summary_row(profile_key, row, label_suffix)
    _append_final_trace_row(profile_key, row, label_suffix)
    _handle_manual_review_or_auto_save(
        profile_key, item, summary, decision, outcome, label_suffix, matching_config
    )


def _handle_manual_review_or_auto_save(
    profile_key, item, summary, decision, outcome, label_suffix, matching_config
) -> None:
    """Handle manual review or auto-save based on config."""
    requires_review = manual_review_required(item, summary.status, outcome, matching_config)
    if requires_review:
        append_manual_review_artifacts(
            profile_key, item, summary, decision, outcome, label_suffix, matching_config
        )
    elif matching_config and matching_config.enable_auto_save_verified_match:
        _auto_save_verified_match(item, decision)


def _auto_save_verified_match(item: Item, decision) -> None:
    """Auto-save verified matches to manual review store."""
    if not decision or not decision.best_match:
        return

    match = decision.best_match
    if match.score == 999.0 and "Approved by saved manual review" in (decision.final_reason or ""):
        return

    store = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB)
    if _preserve_existing_decision(store.lookup(item.code, item.name)):
        return

    _create_and_save_decision(item, match, store)


def _create_and_save_decision(item, match, store) -> None:
    """Create and save auto-matched decision."""
    store_id = candidate_store_product_id(match.data)
    name_en = candidate_name(match.data)
    name_ar = candidate_ar(match.data)

    run = current_artifact_run()
    run_id = run.directory.name if run else ""

    new_decision = ManualReviewDecision(
        item_code=item.code, item_name=item.name, approved=True,
        correct_store_product_id=store_id, manual_decision="auto_matched",
        correct_query="", run_id=run_id, correct_product_name=name_en,
        correct_product_name_ar=name_ar
    )
    store.upsert(new_decision)


def _preserve_existing_decision(existing) -> bool:
    """Return whether a saved human decision must survive auto-save overwrite."""
    return bool(existing and existing.manual_decision in ("approved_match", "not_matching"))


def append_manual_review_artifacts(
    profile_key: str, item: Item, summary: OrderResultSummary, decision, outcome,
    label_suffix: str | None = None, matching_config=None
) -> None:
    """Append one manual-review row to CSV and TXT artifacts, and candidates to JSONL."""
    from ...core.order_run_artifact_rows import text_block

    row = manual_review_row(item, summary, decision, outcome, matching_config)
    append_csv_artifact(profile_key, "manual_review", [row], label_suffix)
    append_text_artifact(profile_key, "manual_review", text_block("manual_review", row), label_suffix)
    _save_review_candidates_if_available(decision, item)


def _save_review_candidates_if_available(decision, item) -> None:
    """Save review candidates to JSONL if available."""
    run = current_artifact_run()
    if run and decision:
        options = review_candidate_options(decision, limit=5)
        append_review_candidates(run.directory, item.code, item.name, options)


__all__ = [
    "append_order_ai_trace_artifacts",
    "append_order_item_artifacts",
    "append_manual_review_artifacts",
    "_preserve_existing_decision",
]
