"""Tawreed order flow orchestration - re-exports from split modules."""

from __future__ import annotations

from typing import Iterable

from src.core.utils.excel import Item
from .tawreed_order_processing import OrderItemProcessor
from .tawreed_order_summary import OrderSummaryRecorder

# Re-export from split modules
from .tawreed_order_placement import (
    _SkipItem,
    _NoResultsItem,
    _artifact_details,
    _save_api_contract_capture,
    OrderPlacementFlow,
)
from .tawreed_order_match import MatchOnlyFlow
from .tawreed_order_delegation import OrderFlowDelegation


# ============================================================================
# TawreedOrderFlow
# ============================================================================

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
        
        # Initialize flow handlers with shared components
        self._placement_flow = OrderPlacementFlow(bot, self.item_processor, self.summary_recorder)
        self._match_flow = MatchOnlyFlow(bot, self.item_processor, self.summary_recorder)
        self._delegation = OrderFlowDelegation(self.item_processor, self.summary_recorder)

    def place_order_from_items(self, items: Iterable[Item]) -> None:
        """Place an order by processing each item from the provided iterable."""
        return self._placement_flow.place_order_from_items(items)

    def match_items_only(self, items: Iterable[Item]) -> None:
        """Match Tawreed products for each item without adding anything to the cart."""
        return self._match_flow.match_items_only(items)

    def _process_single_item(self, page, item):
        """Add one item or save artifacts when a technical failure happens."""
        return self._placement_flow._process_single_item(page, item)

    def _process_items(self, page, items):
        """Process each requested Excel item on the current order page."""
        return self._placement_flow._process_items(page, items)

    def _run_order_session(self, page, items):
        """Prepare the page and process items within an active order session."""
        return self._placement_flow._run_order_session(page, items)

    def _process_single_match_only_item(self, page, item):
        """Match one item without running any add-to-cart action."""
        return self._match_flow._process_single_match_only_item(page, item)

    def _run_match_only_session(self, page, items):
        """Prepare Tawreed and process item matching without cart actions."""
        return self._match_flow._run_match_only_session(page, items)

    # Delegation methods for backward compatibility
    def _add_item(self, page, item):
        """Add one item using either the products-page flow or the legacy configured flow."""
        return self._delegation._add_item(page, item)

    def _match_item_only(self, page, item):
        """Run Tawreed matching for one item without opening the cart dialog."""
        return self._delegation._match_item_only(page, item)

    def _ensure_match_only_surface(self, page):
        """Ensure match-only can use Tawreed's product-search surface."""
        return self._delegation._ensure_match_only_surface(page)

    def _is_products_page(self, page):
        """Return whether the current page is Tawreed's products ordering page."""
        return self._delegation._is_products_page(page)

    def _add_item_with_configured_flow(self, page, item):
        """Execute the selector-driven fallback flow for non-products ordering pages."""
        return self._delegation._add_item_with_configured_flow(page, item)

    def _pick_configured_search_result(self, page, search):
        """Select the configured search result when that selector exists."""
        return self._delegation._pick_configured_search_result(page, search)

    def _fill_configured_quantity(self, page, quantity):
        """Fill the configured quantity input when that selector exists."""
        return self._delegation._fill_configured_quantity(page, quantity)

    def _pick_warehouse_if_needed(self, page):
        """Pick a warehouse row from a warehouse chooser when that flow is active."""
        return self._delegation._pick_warehouse_if_needed(page)

    def _warehouse_mode(self):
        """Return the configured warehouse-selection mode."""
        return self._delegation._warehouse_mode()

    def _click_warehouse_row(self, page, row):
        """Click the warehouse pick button for the provided row."""
        return self._delegation._click_warehouse_row(page, row)

    def _wait_for_legacy_add_completion(self, page):
        """Wait briefly for the legacy add-item flow to settle after submission."""
        return self._delegation._wait_for_legacy_add_completion(page)

    def _wait_for_warehouse_selection(self, page):
        """Wait briefly for the warehouse chooser to settle after selecting a row."""
        return self._delegation._wait_for_warehouse_selection(page)

    def _order_surface_selector(self):
        """Return the selector that best indicates the order surface is ready."""
        return self._delegation._order_surface_selector()

    def _order_surface_ready(self, page):
        """Return whether the products ordering surface is already interactive."""
        return self._delegation._order_surface_ready(page)

    def _prepare_order_page(self, page):
        """Open the site and navigate to the ordering surface for item processing."""
        return self._delegation._prepare_order_page(page)

    def _record_item_summary(self, item, status, reason, elapsed_seconds, match_elapsed_seconds):
        """Append one execution-summary row for the processed item."""
        return self._delegation._record_item_summary(item, status, reason, elapsed_seconds, match_elapsed_seconds)

    def _record_match_only_summary(self, item, status, reason, elapsed_seconds, match_elapsed_seconds):
        """Append one detailed match-only summary for the processed item."""
        return self._delegation._record_match_only_summary(item, status, reason, elapsed_seconds, match_elapsed_seconds)

    def _build_item_summary(self, status, reason, elapsed, match_elapsed):
        """Build a compact summary object from the current bot state."""
        return self._delegation._build_item_summary(status, reason, elapsed, match_elapsed)

    def _skip_status(self, reason):
        """Return the structured summary status for one skipped item."""
        return self._delegation._skip_status(reason)

    def _failure_status(self, reason):
        """Return the structured summary status for one failed item."""
        return self._delegation._failure_status(reason)

    def _unmatched_decision_status(self):
        """Return a more precise status for a rejected but recognized candidate."""
        return self._delegation._unmatched_decision_status()


__all__ = [
    # Re-exports
    "_SkipItem",
    "_NoResultsItem",
    "_artifact_details",
    "_save_api_contract_capture",
    "OrderPlacementFlow",
    "MatchOnlyFlow",
    "OrderFlowDelegation",
    # Main class
    "TawreedOrderFlow",
]
