"""Tawreed order flow orchestration."""

from __future__ import annotations

import time
from contextlib import nullcontext
from typing import Iterable

from playwright.sync_api import Page, sync_playwright

from ..core.manual_review_runtime import (
    manual_review_cache_context,
    preload_manual_review_decisions,
)
from ..core.utils.excel import Item
from .tawreed_api_discovery import begin_api_contract_capture, save_api_contract_capture
from .tawreed_artifacts import dump_artifacts
from .tawreed_checkout import confirm_order
from .tawreed_order_exceptions import _SkipItem, _NoResultsItem
from .tawreed_order_processing import OrderItemProcessor
from .tawreed_order_summary import OrderSummaryRecorder
from .tawreed_session import (
    close_browser,
    close_context,
    open_order_page,
)


class TawreedOrderFlow:
    """Handles Tawreed order placement and item processing."""

    def __init__(self, bot):
        """Initialize order flow with bot instance."""
        self.bot = bot
        self.skip_item_exception = _SkipItem
        self.no_results_exception = _NoResultsItem

        # Initialize sub-modules
        self.item_processor = OrderItemProcessor(bot)
        self.summary_recorder = OrderSummaryRecorder(bot)

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
                # Enable detailed API capture
                from .tawreed_api_discovery_enhanced import (
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
                    # Save enhanced capture
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
        with sync_playwright() as p:
            browser, context, page = open_order_page(
                p, self.bot.config.runtime, self.bot.state_path, debug_browser=self.bot.debug_browser
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
        started_at = time.perf_counter()
        try:
            context = manual_review_cache_context(preload_manual_review_decisions(items))
        except Exception:
            return nullcontext()
        self.bot._record_pending_item_timing(
            "manual_review_lookup_seconds", time.perf_counter() - started_at
        )
        return context

    def _run_match_only_with_artifacts(self, page: Page, items: Iterable[Item]) -> None:
        """Run match-only browser flow and capture diagnostics on failure."""
        try:
            self._run_match_only_session(page, items)
        except Exception as error:
            self._handle_match_only_error(page, error)
            raise

    def _handle_match_only_error(self, page: Page, error: Exception) -> None:
        """Capture diagnostics for match-only failures."""
        dump_artifacts(
            page,
            self.bot.profile_key,
            label="match_only_flow_error",
            details=_artifact_details("match_only_flow_error", error),
        )

    def _run_match_only_session(self, page: Page, items: Iterable[Item]) -> None:
        """Prepare Tawreed and process item matching without cart actions."""
        self.item_processor.prepare_order_page(page)
        completed = self._process_match_only_items(page, items)
        if completed and not self.bot._stop_requested():
            print(f"[{self.bot.profile_key}] Match-only run completed. Cart was unchanged.")
        else:
            print(
                f"[{self.bot.profile_key}] Stop requested or incomplete. Matching stopped."
            )

    def _process_match_only_items(self, page: Page, items: Iterable[Item]) -> bool:
        """Run matching only for each requested Excel item."""
        matched_any = False
        for item in items:
            if self.bot._stop_before_item(item):
                return False
            matched_any = (
                self._process_single_match_only_item(page, item) or matched_any
            )
        return matched_any

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
        started_at = time.perf_counter()
        self.bot._reset_last_item_state()
        try:
            self.summary_recorder.close_visible_dialogs_timed(page)
            self.item_processor.add_item(page, item)
            # Skip close_visible_dialogs after success - waste of time
            self.summary_recorder.record_success(item, started_at)
            return True
        except _SkipItem as error:
            self.summary_recorder.close_visible_dialogs_timed(page)
            self.summary_recorder.record_skip(item, error, started_at)
            return False
        except Exception as error:
            self.summary_recorder.record_failure(page, item, error, started_at)
            return False

    def _process_single_match_only_item(self, page: Page, item: Item) -> bool:
        """Match one item without running any add-to-cart action."""
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

    # Delegation methods for backward compatibility
    def _add_item(self, page, item):
        """Add one item using either the products-page flow or the legacy configured flow."""
        return self.item_processor.add_item(page, item)

    def _match_item_only(self, page, item):
        """Run Tawreed matching for one item without opening the cart dialog."""
        return self.item_processor.match_item_only(page, item)

    def _ensure_match_only_surface(self, page):
        """Ensure match-only can use Tawreed's product-search surface."""
        return self.item_processor.ensure_match_only_surface(page)

    def _is_products_page(self, page):
        """Return whether the current page is Tawreed's products ordering page."""
        return self.item_processor.is_products_page(page)

    def _add_item_with_configured_flow(self, page, item):
        """Execute the selector-driven fallback flow for non-products ordering pages."""
        return self.item_processor.add_item_with_configured_flow(page, item)

    def _pick_configured_search_result(self, page, search):
        """Select the configured search result when that selector exists."""
        return self.item_processor.pick_configured_search_result(page, search)

    def _fill_configured_quantity(self, page, quantity):
        """Fill the configured quantity input when that selector exists."""
        return self.item_processor.fill_configured_quantity(page, quantity)

    def _pick_warehouse_if_needed(self, page):
        """Pick a warehouse row from a warehouse chooser when that flow is active."""
        return self.item_processor.pick_warehouse_if_needed(page)

    def _warehouse_mode(self):
        """Return the configured warehouse-selection mode."""
        return self.item_processor.warehouse_mode()

    def _click_warehouse_row(self, page, row):
        """Click the warehouse pick button for the provided row."""
        return self.item_processor.click_warehouse_row(page, row)

    def _wait_for_legacy_add_completion(self, page):
        """Wait briefly for the legacy add-item flow to settle after submission."""
        return self.item_processor.wait_for_legacy_add_completion(page)

    def _wait_for_warehouse_selection(self, page):
        """Wait briefly for the warehouse chooser to settle after selecting a row."""
        return self.item_processor.wait_for_warehouse_selection(page)

    def _order_surface_selector(self):
        """Return the selector that best indicates the order surface is ready."""
        return self.item_processor.order_surface_selector()

    def _order_surface_ready(self, page):
        """Return whether the products ordering surface is already interactive."""
        return self.item_processor.order_surface_ready(page)

    def _prepare_order_page(self, page):
        """Open the site and navigate to the ordering surface for item processing."""
        return self.item_processor.prepare_order_page(page)

    def _record_item_summary(self, item, status, reason, elapsed_seconds, match_elapsed_seconds):
        """Append one execution-summary row for the processed item."""
        return self.summary_recorder.record_item_summary(item, status, reason, elapsed_seconds, match_elapsed_seconds)

    def _record_match_only_summary(self, item, status, reason, elapsed_seconds, match_elapsed_seconds):
        """Append one detailed match-only summary for the processed item."""
        return self.summary_recorder.record_match_only_summary(item, status, reason, elapsed_seconds, match_elapsed_seconds)

    def _build_item_summary(self, status, reason, elapsed, match_elapsed):
        """Build a compact summary object from the current bot state."""
        return self.summary_recorder.build_item_summary(status, reason, elapsed, match_elapsed)

    def _skip_status(self, reason):
        """Return the structured summary status for one skipped item."""
        return self.summary_recorder.skip_status(reason)

    def _failure_status(self, reason):
        """Return the structured summary status for one failed item."""
        return self.summary_recorder.failure_status(reason)

    def _unmatched_decision_status(self):
        """Return a more precise status for a rejected but recognized candidate."""
        return self.summary_recorder.unmatched_decision_status()


def _artifact_details(label: str, error: Exception, **extra: object) -> str:
    """Build plain-text diagnostic details for saved failure artifacts."""
    lines = [f"label={label}", f"error_type={type(error).__name__}", f"error={error}"]
    for key, value in extra.items():
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _save_api_contract_capture(captured: list[dict]) -> None:
    try:
        save_api_contract_capture(captured)
    except Exception:
        pass
