"""Builder methods for order summary."""

from __future__ import annotations

import time

from ..core.utils.excel import Item
from .tawreed_match_logs import OrderResultSummary, append_order_result_summary
from .tawreed_match_only_summary import append_match_only_summary
from .tawreed_order_run_artifacts import append_order_item_artifacts


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
