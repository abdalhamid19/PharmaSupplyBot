"""Failure recording methods for order summary."""

from __future__ import annotations

import time

from ..core.utils.excel import Item
from .tawreed_artifacts import dump_artifacts
from .tawreed_summary_utils import _item_error_label, _item_error_details, _console_safe


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
