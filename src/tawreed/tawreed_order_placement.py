"""Tawreed order placement flow with exception handling."""

from __future__ import annotations

from typing import Iterable

from playwright.sync_api import Page, sync_playwright

from ..core.manual_review_runtime import (
    manual_review_cache_context,
    preload_manual_review_decisions,
)
from ..core.utils.excel import Item
from .tawreed_api_contract import begin_api_contract_capture
from .tawreed_artifacts import dump_artifacts
from .tawreed_checkout import confirm_order
from .tawreed_order_processing import OrderItemProcessor
from .tawreed_order_summary import OrderSummaryRecorder
from .tawreed_session import close_browser, close_context, open_order_page


# ============================================================================
# Exceptions
# ============================================================================

class _SkipItem(Exception):
    """Signal that one item should be skipped without failing the whole order run."""
    pass


class _NoResultsItem(_SkipItem):
    """Signal that one item had no Tawreed results and should be skipped quickly."""
    pass


# ============================================================================
# Utility Functions
# ============================================================================

def _artifact_details(label: str, error: Exception, **extra: object) -> str:
    """Build plain-text diagnostic details for saved failure artifacts."""
    lines = [f"label={label}", f"error_type={type(error).__name__}", f"error={error}"]
    for key, value in extra.items():
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _save_api_contract_capture(captured: list[dict]) -> None:
    """Save API contract capture data."""
    try:
        from .tawreed_api_contract import save_api_contract_capture
        save_api_contract_capture(captured)
    except Exception:
        pass


# ============================================================================
# OrderPlacementFlow
# ============================================================================

class OrderPlacementFlow:
    """Handles order placement and item processing."""

    def __init__(self, bot, item_processor=None, summary_recorder=None):
        self.bot = bot
        self.skip_item_exception = _SkipItem
        self.item_processor = item_processor or OrderItemProcessor(bot)
        self.summary_recorder = summary_recorder or OrderSummaryRecorder(bot)

    def place_order_from_items(self, items: Iterable[Item]) -> None:
        """Place an order by processing each item from the provided iterable."""
        self.bot._ensure_valid_auth()
        items = list(items)
        with self._manual_review_cache_for_items(items):
            if self.bot._try_api_order(items):
                return
            with sync_playwright() as p:
                browser, context, page = open_order_page(
                    p,
                    self.bot.config.runtime,
                    self.bot.state_path,
                    debug_browser=self.bot.debug_browser,
                )
                from .tawreed_api_contract import (
                    begin_detailed_api_capture,
                    save_captured_requests,
                )
                captured = begin_detailed_api_capture(page)
                api_capture = begin_api_contract_capture(page)
                try:
                    self._run_order_session(page, items)
                except Exception as error:
                    dump_artifacts(
                        page,
                        self.bot.profile_key,
                        label="order_flow_error",
                        details=_artifact_details("order_flow_error", error),
                    )
                    raise
                finally:
                    if captured:
                        save_captured_requests(captured, self.bot.profile_key, "order_run_capture")
                    _save_api_contract_capture(api_capture)
                    close_context(context)
                    close_browser(browser)

    def _run_order_session(self, page: Page, items: Iterable[Item]) -> None:
        """Prepare the page and process items within an active order session."""
        self.item_processor.prepare_order_page(page)
        completed = self._process_items(page, items)
        if completed and not self.bot._stop_requested():
            if not self.bot.config.runtime.submit_order:
                print(
                    f"[{self.bot.profile_key}] Items added to cart. "
                    "Final order submission is disabled for manual human review."
                )
                return
            confirm_order(page, self.bot.selectors, self.bot.config.runtime.timeout_ms)
        else:
            print(
                f"[{self.bot.profile_key}] Stop requested or incomplete. Order confirmation skipped."
            )

    def _process_items(self, page: Page, items: Iterable[Item]) -> bool:
        """Process each requested Excel item on the current order page."""
        added_any = False
        for item in items:
            if self.bot._stop_before_item(item):
                return False
            added_any = self._process_single_item(page, item) or added_any
        return added_any

    def _process_single_item(self, page: Page, item: Item) -> bool:
        """Add one item or save artifacts when a technical failure happens."""
        import time
        started_at = time.perf_counter()
        self.bot._reset_last_item_state()
        try:
            self.summary_recorder.close_visible_dialogs_timed(page)
            self.item_processor.add_item(page, item)
            self.summary_recorder.record_success(item, started_at)
            return True
        except _SkipItem as error:
            self.summary_recorder.close_visible_dialogs_timed(page)
            self.summary_recorder.record_skip(item, error, started_at)
            return False
        except Exception as error:
            self.summary_recorder.record_failure(page, item, error, started_at)
            return False

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


__all__ = [
    "_SkipItem",
    "_NoResultsItem",
    "_artifact_details",
    "_save_api_contract_capture",
    "OrderPlacementFlow",
]
