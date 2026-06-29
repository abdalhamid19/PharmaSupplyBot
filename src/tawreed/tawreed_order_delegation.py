"""Tawreed order flow delegation for backward compatibility."""

from __future__ import annotations

from .tawreed_summary import SummaryBuilder, SummaryStatus


# ============================================================================
# OrderFlowDelegation
# ============================================================================

class OrderFlowDelegation:
    """Provides delegation methods for backward compatibility."""

    def __init__(self, item_processor, summary_recorder):
        self.item_processor = item_processor
        self.summary_recorder = summary_recorder
        self._status = SummaryStatus(summary_recorder.bot)
        self._builder = SummaryBuilder(summary_recorder.bot)

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
        return self._builder.build_item_summary(status, reason, elapsed, match_elapsed)

    def _skip_status(self, reason):
        """Return the structured summary status for one skipped item."""
        return self._status.skip_status(reason)

    def _failure_status(self, reason):
        """Return the structured summary status for one failed item."""
        return self._status.failure_status(reason)

    def _unmatched_decision_status(self):
        """Return a more precise status for a rejected but recognized candidate."""
        return self._status.unmatched_decision_status()


__all__ = [
    "OrderFlowDelegation",
]
