"""Success recording methods for order summary."""

from __future__ import annotations

import time

from ..core.utils.excel import Item
from .tawreed_summary_utils import _console_safe


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
