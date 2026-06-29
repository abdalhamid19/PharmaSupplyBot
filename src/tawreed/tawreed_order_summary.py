"""Order summary and recording logic for Tawreed order processing."""

from __future__ import annotations

import time

from ..core.artifact_run import current_artifact_run
from ..core.manual_review_candidate_store import append_review_candidates
from ..core.manual_review_candidates import review_candidate_options
from ..core.manual_review_store import ManualReviewDecision, ManualReviewStore, DEFAULT_MANUAL_REVIEW_DB
from ..core.order_ai_artifacts import order_ai_trace_rows
from ..core.order_ai_matching import candidate_ar, candidate_name
from ..core.order_run_artifact_rows import (
    manual_review_required,
    manual_review_row,
    order_item_summary_row,
    text_block,
)
from ..core.utils.excel import Item
from ..core.candidate_identity import candidate_store_product_id
from .tawreed_artifacts import dump_artifacts, append_csv_artifact, append_text_artifact
from .tawreed_dialogs import visible_overlay_diagnostics
from .tawreed_match_logs import OrderResultSummary, append_order_result_summary
from .tawreed_match_only import append_match_only_summary
from .tawreed_summary import SummaryBuilder, SummaryDialogHandler, SummaryStatus, _item_error_label, _item_error_details, _console_safe, _artifact_details


# ============================================================================
# Order run artifacts functions (from tawreed_order_run_artifacts.py)
# ============================================================================

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


def append_order_item_artifacts(profile_key: str, item: Item, summary: OrderResultSummary, decision, outcome, label_suffix: str | None = None, matching_config=None) -> None:
    """Append one item summary row and optional manual-review row."""
    row = order_item_summary_row(item, summary, decision, outcome, matching_config)
    _append_item_summary_row(profile_key, row, label_suffix)
    _append_final_trace_row(profile_key, row, label_suffix)
    _handle_manual_review_or_auto_save(profile_key, item, summary, decision, outcome, label_suffix, matching_config)


def _handle_manual_review_or_auto_save(profile_key, item, summary, decision, outcome, label_suffix, matching_config):
    """Handle manual review or auto-save based on config."""
    requires_review = manual_review_required(item, summary.status, outcome, matching_config)
    if requires_review:
        append_manual_review_artifacts(profile_key, item, summary, decision, outcome, label_suffix, matching_config)
    elif matching_config and matching_config.enable_auto_save_verified_match:
        _auto_save_verified_match(item, decision)


def _auto_save_verified_match(item: Item, decision) -> None:
    if not decision or not decision.best_match:
        return
    
    match = decision.best_match
    if match.score == 999.0 and "Approved by saved manual review" in (decision.final_reason or ""):
        return
    
    store = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB)
    if _preserve_existing_decision(store.lookup(item.code, item.name)):
        return
    
    _create_and_save_decision(item, match, store)


def _create_and_save_decision(item, match, store):
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


def append_manual_review_artifacts(profile_key: str, item: Item, summary: OrderResultSummary, decision, outcome, label_suffix: str | None = None, matching_config=None) -> None:
    """Append one manual-review row to CSV and TXT artifacts, and candidates to JSONL."""
    row = manual_review_row(item, summary, decision, outcome, matching_config)
    append_csv_artifact(profile_key, "manual_review", [row], label_suffix)
    append_text_artifact(profile_key, "manual_review", text_block("manual_review", row), label_suffix)
    _save_review_candidates_if_available(decision, item)


def _save_review_candidates_if_available(decision, item):
    """Save review candidates to JSONL if available."""
    run = current_artifact_run()
    if run and decision:
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


# ============================================================================
# Base class (from tawreed_order_summary_main.py)
# ============================================================================

class OrderSummaryRecorderBase:
    """Base class for order summary recorder."""

    def __init__(self, bot):
        """Initialize summary recorder with bot instance."""
        self.bot = bot
        self._summary_builder = SummaryBuilder(bot)
        self._status = SummaryStatus(bot)
        self._dialog_handler = SummaryDialogHandler(bot)

    def close_visible_dialogs_timed(self, page) -> None:
        """Close visible dialogs and accumulate the item-level wait cost."""
        self._dialog_handler.close_visible_dialogs_timed(page)


# ============================================================================
# Success mixin (from tawreed_order_summary_success.py)
# ============================================================================

class OrderSummaryRecorderSuccessMixin:
    """Success recording methods for OrderSummaryRecorder."""

    def record_success(self, item: Item, started_at: float) -> None:
        """Record a successful add-to-cart summary."""
        self.record_item_summary(
            item,
            status="added-to-cart",
            reason="Added to cart.",
            elapsed_seconds=time.perf_counter() - started_at,
            match_elapsed_seconds=self.bot.last_match_elapsed_seconds,
        )

    def record_match_only_success(self, item: Item, started_at: float) -> None:
        """Record a successful product match that did not touch the cart."""
        self.record_match_only_summary(
            item,
            status="matched-only",
            reason="Matched product only; item was not added to cart.",
            elapsed_seconds=time.perf_counter() - started_at,
            match_elapsed_seconds=self.bot.last_match_elapsed_seconds,
        )

    def record_match_only_skip(
        self, item: Item, error: Exception, started_at: float
    ) -> None:
        """Record a skipped item during match-only mode."""
        reason = str(error)
        self.record_match_only_summary(
            item,
            self._status.skip_status(reason),
            reason,
            time.perf_counter() - started_at,
            self.bot.last_match_elapsed_seconds,
        )
        print(
            _console_safe(
                f"[{self.bot.profile_key}] Skipped item {item.code} / {item.name}: {error}"
            )
        )


# ============================================================================
# Failure mixin (from tawreed_order_summary_failure.py)
# ============================================================================

class OrderSummaryRecorderFailureMixin:
    """Failure recording methods for OrderSummaryRecorder."""

    def record_match_only_failure(
        self, page, item: Item, error: Exception, started_at: float
    ) -> None:
        """Record a failed match-only item and capture diagnostics."""
        reason = str(error)
        self._dialog_handler.close_visible_dialogs_timed(page)
        self.record_match_only_summary(
            item,
            self._status.failure_status(reason),
            reason,
            time.perf_counter() - started_at,
            self.bot.last_match_elapsed_seconds,
        )
        self.print_failed_item(item, error)
        dump_artifacts(
            page,
            self.bot.profile_key,
            _item_error_label(item),
            _item_error_details(page, item, error),
        )

    def record_skip(self, item: Item, error: Exception, started_at: float) -> None:
        """Record a skipped item summary."""
        reason = str(error)
        self.record_item_summary(
            item,
            status=self._status.skip_status(reason),
            reason=reason,
            elapsed_seconds=time.perf_counter() - started_at,
            match_elapsed_seconds=self.bot.last_match_elapsed_seconds,
        )
        print(
            _console_safe(
                f"[{self.bot.profile_key}] Skipped item {item.code} / {item.name}: {error}"
            )
        )

    def record_failure(
        self, page, item: Item, error: Exception, started_at: float
    ) -> None:
        """Record a technical failure and capture diagnostic artifacts."""
        reason = str(error)
        self._dialog_handler.close_visible_dialogs_timed(page)
        self.record_failure_summary(item, reason, started_at)
        self.print_failed_item(item, error)
        dump_artifacts(
            page,
            self.bot.profile_key,
            label=_item_error_label(item),
            details=_item_error_details(page, item, error),
        )

    def record_failure_summary(self, item: Item, reason: str, started_at: float) -> None:
        """Append the summary row for one failed item."""
        self.record_item_summary(
            item,
            self._status.failure_status(reason),
            reason,
            time.perf_counter() - started_at,
            self.bot.last_match_elapsed_seconds,
        )

    def print_failed_item(self, item: Item, error: Exception) -> None:
        """Print one console-safe failed item message."""
        message = f"[{self.bot.profile_key}] Failed item {item.code} / {item.name}: {error}"
        print(_console_safe(message))


# ============================================================================
# Builders mixin (from tawreed_order_summary_builders.py)
# ============================================================================

class OrderSummaryRecorderBuildersMixin:
    """Builder methods for OrderSummaryRecorder."""

    def record_item_summary(
        self,
        item: Item,
        status: str,
        reason: str,
        elapsed_seconds: float,
        match_elapsed_seconds: float,
    ) -> None:
        """Append one execution-summary row for the processed item."""
        summary = self._summary_builder.build_item_summary(
            status, reason, elapsed_seconds, match_elapsed_seconds
        )
        append_order_result_summary(
            self.bot.profile_key, item, summary, label_suffix=self.bot.summary_label_suffix
        )
        self.record_order_run_artifacts(item, summary)

    def record_match_only_summary(
        self,
        item: Item,
        status: str,
        reason: str,
        elapsed_seconds: float,
        match_elapsed_seconds: float,
    ) -> None:
        """Append one detailed match-only summary for the processed item."""
        summary = self._summary_builder.build_item_summary(
            status, reason, elapsed_seconds, match_elapsed_seconds
        )
        append_match_only_summary(
            self.bot.profile_key,
            item,
            summary,
            self.bot.last_match_decision,
            label_suffix=self.bot.summary_label_suffix,
        )
        self.record_order_run_artifacts(item, summary)

    def record_order_run_artifacts(self, item: Item, summary: OrderResultSummary) -> None:
        """Append per-item summary and manual-review artifacts for this run."""
        append_order_item_artifacts(
            self.bot.profile_key,
            item,
            summary,
            self.bot.last_match_decision,
            self.bot.last_order_ai_outcome,
            self.bot.summary_label_suffix,
            self.bot.config.matching,
        )


# ============================================================================
# Main recorder class (from tawreed_order_summary.py)
# ============================================================================

class OrderSummaryRecorder(
    OrderSummaryRecorderBase,
    OrderSummaryRecorderSuccessMixin,
    OrderSummaryRecorderFailureMixin,
    OrderSummaryRecorderBuildersMixin,
):
    """Handles recording of order summaries and match-only summaries."""
    pass


__all__ = [
    "OrderSummaryRecorder",
    "append_order_ai_trace_artifacts",
    "append_order_item_artifacts",
    "append_manual_review_artifacts",
    "_preserve_existing_decision",
    "dump_artifacts",
]
