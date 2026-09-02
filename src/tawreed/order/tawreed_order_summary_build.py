"""Summary building functions for Tawreed order processing."""

from __future__ import annotations

import logging

from src.core.artifact_run import current_artifact_run
from src.core.manual_review.manual_review_candidate_store import append_review_candidates
from src.core.manual_review.manual_review_candidates import review_candidate_options
from src.core.manual_review.manual_review_store import ManualReviewDecision, ManualReviewStore, DEFAULT_MANUAL_REVIEW_DB
from src.core.ordering.order_run_artifact_rows import manual_review_required, manual_review_row, order_item_summary_row
from src.core.ordering.order_run_persistence import record_run_item
from src.core.utils.excel import Item
from src.core.matching.candidate_identity import candidate_store_product_id
from ..artifacts.tawreed_artifacts import append_csv_artifact, append_text_artifact
from ..matching.tawreed_match_logs import OrderResultSummary
from ..store.tawreed_store_run_payload import active_order_run_key

logger = logging.getLogger(__name__)


def append_order_item_artifacts(
    profile_key: str, item: Item, summary: OrderResultSummary, decision,
    label_suffix: str | None = None, matching_config=None,
    store_snapshot: dict | None = None, database_options: dict | None = None,
) -> None:
    """Append one item summary row and optional manual-review row.

    ``store_snapshot`` carries the item's offering stores so they are persisted
    in the same transaction as the item fact. It is optional so existing callers
    keep working; without it only the item-level facts are stored.
    """
    from .tawreed_order_summary_format import _append_item_summary_row, _append_final_trace_row

    row = order_item_summary_row(item, summary, decision, matching_config)
    _append_item_summary_row(profile_key, row, label_suffix)
    _append_final_trace_row(profile_key, row, label_suffix)
    _persist_order_run_item(row, store_snapshot, database_options)
    _handle_manual_review_or_auto_save(
        profile_key, item, summary, decision, label_suffix, matching_config
    )


def _persist_order_run_item(row, store_snapshot, database_options) -> None:
    """Write one item and its offering stores to the order-runs database."""
    snapshot = dict(store_snapshot or {})
    snapshot.setdefault("source_kind", "tawreed")
    snapshot.setdefault("source_label", _current_profile_key())
    record_run_item(
        active_order_run_key(), row, database_options, **snapshot
    )


def _current_profile_key() -> str:
    """Return the active Tawreed profile key for the current run.

    Falls back to the empty string when the artifact run has not recorded
    one (defensive default for tests and dry-runs).
    """
    from src.core.artifact_run import current_artifact_run

    run = current_artifact_run()
    if run is None:
        return ""
    label = run.profile_key if hasattr(run, "profile_key") else ""
    return str(label or "")


def _handle_manual_review_or_auto_save(
    profile_key, item, summary, decision, label_suffix, matching_config
) -> None:
    """Handle manual review or auto-save based on config."""
    requires_review = manual_review_required(item, summary.status, matching_config)
    if requires_review:
        append_manual_review_artifacts(
            profile_key, item, summary, decision, label_suffix, matching_config
        )
    elif matching_config and matching_config.enable_auto_save_verified_match:
        _auto_save_verified_match(item, decision, matching_config)


def _auto_save_verified_match(item: Item, decision, matching_config=None) -> None:
    """Auto-save verified matches to manual review store."""
    if not decision or not decision.best_match:
        return

    match = decision.best_match
    if match.score == 999.0 and "Approved by saved manual review" in (decision.final_reason or ""):
        return

    # Safety check: skip saving matches that have validation issues.
    # The helper returns (should_skip, reason); unpack it — the previous
    # bare `if <tuple>:` was always truthy and blocked every auto-save,
    # so nothing was ever persisted as auto_matched.
    from src.core.manual_review.manual_review_runtime import should_skip_auto_save_verified_match
    rejection_reason = _decision_rejection_reason(decision)
    skip, skip_reason = should_skip_auto_save_verified_match(
        item,
        match.data,
        rejection_reason,
        enable_manufacturer_check=bool(
            matching_config and matching_config.enable_manufacturer_check
        ),
    )
    if skip:
        _log_auto_save_skip(item, skip_reason)
        return

    store = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB)
    if _preserve_existing_decision(store.lookup(item.code, item.name)):
        return

    _create_and_save_decision(item, match, store)


def _decision_rejection_reason(decision) -> str | None:
    """Return the winning diagnostic's rejection reason, when it is negative.

    MatchDecision has no rejection_reason field; the signal lives on the best
    CandidateMatchDiagnostic. Only a genuine rejection reason is surfaced —
    an accepted candidate's empty string must not block auto-save.
    """
    diagnostics = getattr(decision, "diagnostics", None) or []
    best = max(diagnostics, key=lambda diagnostic: diagnostic.score, default=None)
    reason = getattr(best, "rejection_reason", "") if best else ""
    return reason or None


def _log_auto_save_skip(item: Item, reason: str) -> None:
    """Log why an auto-save was skipped so silent data loss stays visible."""
    logger.info(
        "auto-save skipped",
        extra={"code": item.code, "item_name": item.name, "reason": reason},
    )


def _create_and_save_decision(item, match, store) -> None:
    """Create and save auto-matched decision."""
    store_id = candidate_store_product_id(match.data)
    name_en = str(match.data.get("productNameEn") or match.data.get("productNameEnFallback") or "")
    name_ar = str(match.data.get("productName") or "")

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
    profile_key: str, item: Item, summary: OrderResultSummary, decision,
    label_suffix: str | None = None, matching_config=None
) -> None:
    """Append one manual-review row to CSV and TXT artifacts, and candidates to JSONL."""
    from src.core.ordering.order_run_artifact_rows import text_block

    row = manual_review_row(item, summary, decision, matching_config)
    append_csv_artifact(profile_key, "manual_review", [row], label_suffix)
    append_text_artifact(
        profile_key, "manual_review", text_block("manual_review", row), label_suffix
    )
    _save_review_candidates_if_available(decision, item, matching_config)


def _save_review_candidates_if_available(decision, item, matching_config=None) -> None:
    """Save review candidates to JSONL if available."""
    run = current_artifact_run()
    if run and decision:
        options = review_candidate_options(
            decision, limit=_review_candidate_limit(matching_config)
        )
        append_review_candidates(run.directory, item.code, item.name, options)


def _review_candidate_limit(matching_config=None) -> int:
    """Return configured Manual Review candidate limit for this run."""
    value = getattr(matching_config, "manual_review_save_candidate_limit", 5)
    return max(1, int(value))


__all__ = [
    "append_order_item_artifacts",
    "append_manual_review_artifacts",
    "_preserve_existing_decision",
]
