"""Item processing logic for Tawreed order flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

from src.core.utils.excel import Item
from ..tawreed_constants import PRODUCTS_PAGE_ROUTE
from ..tawreed_navigation import go_to_orders, maybe_switch_pharmacy, start_new_order
from ..products.tawreed_products_flow import add_item_from_products_page
from ..products.tawreed_match_only_metadata import record_match_only_store_metadata
from ..matching.tawreed_search_logic import require_product_match
from ..auth.tawreed_session import close_browser, close_context, open_order_page
from ..matching.tawreed_strategy import max_available_warehouse_row


class OrderItemProcessor:
    """Handles item processing logic for Tawreed orders."""

    def __init__(self, bot):
        """Initialize item processor with bot instance."""
        self.bot = bot

    def add_item(self, page: Page, item: Item) -> None:
        """Add one item using either the products-page flow or the legacy configured flow."""
        if self.is_products_page(page):
            add_item_from_products_page(self.bot, page, item)
            return

        self.add_item_with_configured_flow(page, item)

    def match_item_only(self, page: Page, item: Item) -> None:
        """Run Tawreed matching for one item without opening the cart dialog."""
        self.ensure_match_only_surface(page)
        match, active_query = require_product_match(
            self.bot, page, item, require_available=False
        )
        record_match_only_store_metadata(self.bot, page, match, active_query)
        self.bot.log(f"Match-only accepted {item.code} / {item.name}: {match.query}")

    def ensure_match_only_surface(self, page: Page) -> None:
        """Ensure match-only can use Tawreed's product-search surface."""
        if self.is_products_page(page) or self.order_surface_ready(page):
            return
        self.prepare_order_page(page)
        if not (self.is_products_page(page) or self.order_surface_ready(page)):
            raise RuntimeError("Match-only mode requires Tawreed products page flow.")

    def is_products_page(self, page: Page) -> bool:
        """Return whether the current page is Tawreed's products ordering page."""
        return PRODUCTS_PAGE_ROUTE in page.url

    def add_item_with_configured_flow(self, page: Page, item: Item) -> None:
        """Execute the selector-driven fallback flow for non-products ordering pages."""
        search = page.locator(self.bot.selectors.item_search_input).first
        search.click()
        search.fill("")
        query = item.code if item.code else item.name
        search.fill(query)

        self.pick_configured_search_result(page, search)
        self.fill_configured_quantity(page, item.qty)
        page.locator(self.bot.selectors.add_item_button).first.click()
        self.bot.last_ordered_total_qty = int(item.qty)
        self.wait_for_legacy_add_completion(page)

    def pick_configured_search_result(self, page: Page, search) -> None:
        """Select the configured search result when that selector exists."""
        if not self.bot.selectors.item_first_result:
            return
        try:
            page.locator(self.bot.selectors.item_first_result).first.wait_for(timeout=5000)
            page.locator(self.bot.selectors.item_first_result).first.click()
        except Exception:
            search.press("Enter")

    def fill_configured_quantity(self, page: Page, quantity: int) -> None:
        """Fill the configured quantity input when that selector exists."""
        if not self.bot.selectors.qty_input:
            return
        quantity_input = page.locator(self.bot.selectors.qty_input).first
        quantity_input.fill("")
        quantity_input.fill(str(quantity))

    def pick_warehouse_if_needed(self, page: Page) -> None:
        """Pick a warehouse row from a warehouse chooser when that flow is active."""
        mode = self.warehouse_mode()
        rows = page.locator(self.bot.selectors.warehouse_rows)
        if rows.count() == 0:
            return

        if mode == "first_available":
            self.click_warehouse_row(page, rows.first)
            return

        if mode == "max_available":
            row_index = max_available_warehouse_row(
                rows, self.bot.selectors.warehouse_available_qty
            )
            self.click_warehouse_row(page, rows.nth(row_index))
            return

        raise ValueError(f"Unknown warehouse strategy mode: {mode}")

    def warehouse_mode(self) -> str:
        """Return the configured warehouse-selection mode."""
        return str(self.bot.config.warehouse_strategy.get("mode", "first_available"))

    def click_warehouse_row(self, page: Page, row) -> None:
        """Click the warehouse pick button for the provided row."""
        row.locator(self.bot.selectors.warehouse_pick_button).first.click()
        self.wait_for_warehouse_selection(page)

    def wait_for_legacy_add_completion(self, page: Page) -> None:
        """Wait briefly for the legacy add-item flow to settle after submission."""
        try:
            page.locator(self.bot.selectors.item_search_input).first.wait_for(timeout=1000)
        except Exception:
            pass

    def wait_for_warehouse_selection(self, page: Page) -> None:
        """Wait briefly for the warehouse chooser to settle after selecting a row."""
        try:
            page.locator(self.bot.selectors.warehouse_rows).first.wait_for(
                state="hidden", timeout=1000
            )
        except Exception:
            pass

    def order_surface_selector(self) -> str:
        """Return the selector that best indicates the order surface is ready."""
        if self.bot.selectors.new_order:
            return self.bot.selectors.new_order
        return self.bot.selectors.item_search_input

    def order_surface_ready(self, page: Page) -> bool:
        """Return whether the products ordering surface is already interactive."""
        try:
            page.locator(self.bot.selectors.item_search_input).first.wait_for(timeout=1500)
            return True
        except Exception:
            return False

    def prepare_order_page(self, page: Page) -> None:
        """Open the site and navigate to the ordering surface for item processing."""
        page.goto(self.bot._products_page_url(), wait_until="domcontentloaded")
        maybe_switch_pharmacy(page, self.bot.profile.pharmacy_switch or {})
        if self.order_surface_ready(page):
            return
        go_to_orders(page, self.bot.selectors.go_to_orders, self.order_surface_selector())
        start_new_order(
            page, self.bot.selectors.new_order, self.bot.selectors.item_search_input
        )
