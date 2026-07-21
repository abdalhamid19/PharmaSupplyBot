"""Order summary and recording logic for Tawreed order processing."""

from __future__ import annotations

import logging
import time

from src.core.utils.excel import Item
from ..artifacts.tawreed_artifacts import dump_artifacts
from ..tawreed_dialogs import visible_overlay_diagnostics
from ..matching.tawreed_match_logs import OrderResultSummary
from ..tawreed_summary import (
    SummaryBuilder, SummaryDialogHandler, SummaryStatus,
    _item_error_label, _item_error_details, _artifact_details
)
from .tawreed_order_summary_build import (
    append_order_ai_trace_artifacts,
    append_order_item_artifacts,
    append_manual_review_artifacts,
    _preserve_existing_decision,
)
from .tawreed_order_summary_format import (
    _final_trace_row,
    _append_item_summary_row,
    _append_final_trace_row,
    _text_rows,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Base class
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
# Success mixin
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
        logger.info(
            "skipped item",
            extra={
                "profile": self.bot.profile_key,
                "code": item.code,
                "name": item.name,
                "reason": reason,
            },
        )


# ============================================================================
# Failure mixin
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
        logger.info(
            "skipped item",
            extra={
                "profile": self.bot.profile_key,
                "code": item.code,
                "name": item.name,
                "reason": reason,
            },
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
        """Log a single failed-item diagnostic via the structured logger."""
        logger.warning(
            "failed item",
            extra={
                "profile": self.bot.profile_key,
                "code": item.code,
                "name": item.name,
                "reason": str(error),
            },
        )


# ============================================================================
# Builders mixin
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
        from ..matching.tawreed_match_logs import append_order_result_summary

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
        from ..matching.tawreed_match_only import append_match_only_summary

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
# Main recorder class
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
