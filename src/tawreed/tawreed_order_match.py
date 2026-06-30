"""Tawreed match-only flow without cart actions."""

from __future__ import annotations

from typing import Iterable

from ..core.manual_review_runtime import (
    manual_review_cache_context,
    preload_manual_review_decisions,
)
from ..core.utils.excel import Item
from .tawreed_api_contract import begin_api_contract_capture
from .tawreed_artifacts import dump_artifacts
from .tawreed_order_processing import OrderItemProcessor
from .tawreed_order_summary import OrderSummaryRecorder
from .tawreed_session import close_browser, close_context, open_order_page
from .tawreed_order_placement import _SkipItem, _artifact_details, _save_api_contract_capture


# ============================================================================
# MatchOnlyFlow
# ============================================================================

class MatchOnlyFlow:
    """Handles match-only product matching without cart actions."""

    def __init__(self, bot, item_processor=None, summary_recorder=None):
        self.bot = bot
        self.skip_item_exception = _SkipItem
        self.item_processor = item_processor or OrderItemProcessor(bot)
        self.summary_recorder = summary_recorder or OrderSummaryRecorder(bot)

    def match_items_only(self, items: Iterable[Item]) -> None:
        """Match Tawreed products for each item without adding anything to the cart."""
        self.bot._ensure_valid_auth()
        items = list(items)
        with self._manual_review_cache_for_items(items):
            if self.bot._try_api_match_only(items):
                return
            self._match_items_browser_mode(items)

    def _match_items_browser_mode(self, items: list[Item]) -> None:
        """Match items using browser mode."""
        from playwright.sync_api import Page, sync_playwright
        
        with sync_playwright() as p:
            browser, context, page = open_order_page(
                p,
                self.bot.config.runtime,
                self.bot.state_path,
                debug_browser=self.bot.debug_browser
            )
            api_capture = begin_api_contract_capture(page)
            try:
                self._run_match_only_with_artifacts(page, items)
            finally:
                _save_api_contract_capture(api_capture)
                close_context(context)
                close_browser(browser)

    def _manual_review_cache_for_items(self, items: list[Item]):
        """Return a run-scoped manual-review decision cache context."""
        import time
        from contextlib import nullcontext
        
        started_at = time.perf_counter()
        try:
            context = manual_review_cache_context(preload_manual_review_decisions(items))
        except Exception:
            return nullcontext()
        self.bot._record_pending_item_timing(
            "manual_review_lookup_seconds", time.perf_counter() - started_at
        )
        return context

    def _run_match_only_with_artifacts(self, page, items: Iterable[Item]) -> None:
        """Run match-only browser flow and capture diagnostics on failure."""
        try:
            self._run_match_only_session(page, items)
        except Exception as error:
            dump_artifacts(
                page,
                self.bot.profile_key,
                label="match_only_flow_error",
                details=_artifact_details("match_only_flow_error", error),
            )
            raise

    def _run_match_only_session(self, page, items: Iterable[Item]) -> None:
        """Prepare Tawreed and process item matching without cart actions."""
        self.item_processor.prepare_order_page(page)
        completed = self._process_match_only_items(page, items)
        if completed and not self.bot._stop_requested():
            print(f"[{self.bot.profile_key}] Match-only run completed. Cart was unchanged.")
        else:
            print(
                f"[{self.bot.profile_key}] Stop requested or incomplete. Matching stopped."
            )

    def _process_match_only_items(self, page, items: Iterable[Item]) -> bool:
        """Run matching only for each requested Excel item."""
        matched_any = False
        for item in items:
            if self.bot._stop_before_item(item):
                return False
            matched_any = (
                self._process_single_match_only_item(page, item) or matched_any
            )
        return matched_any

    def _process_single_match_only_item(self, page, item: Item) -> bool:
        """Match one item without running any add-to-cart action."""
        import time
        started_at = time.perf_counter()
        self.bot._reset_last_item_state()
        try:
            self.summary_recorder.close_visible_dialogs_timed(page)
            self.item_processor.match_item_only(page, item)
            self.summary_recorder.close_visible_dialogs_timed(page)
            self.summary_recorder.record_match_only_success(item, started_at)
            return True
        except _SkipItem as error:
            self.summary_recorder.close_visible_dialogs_timed(page)
            self.summary_recorder.record_match_only_skip(item, error, started_at)
            return False
        except Exception as error:
            self.summary_recorder.record_match_only_failure(page, item, error, started_at)
            return False


__all__ = [
    "MatchOnlyFlow",
]
