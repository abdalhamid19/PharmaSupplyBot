"""Playwright automation for product search and Tawreed ordering."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from .config_models import AppConfig, ProfileConfig
from .excel import Item
from .selectors import _selectors
from .tawreed_artifacts import dump_artifacts
from .tawreed_checkout import confirm_order
from .tawreed_match_logs import write_match_log
from .tawreed_navigation import go_to_orders, maybe_switch_pharmacy, start_new_order
from .tawreed_products_flow import add_item_from_products_page
from .tawreed_session import (
    attempt_env_login,
    close_browser,
    close_context,
    ensure_logged_in,
    open_auth_page,
    open_order_page,
    print_auth_instructions,
    print_login_detection_result,
    save_session_state,
    wait_for_login_detection,
    wait_for_network_idle,
)
from .tawreed_strategy import max_available_warehouse_row


class _SkipItem(Exception):
    """Signal that one item should be skipped without failing the whole order run."""

    pass


class TawreedBot:
    """Coordinate Tawreed authentication, product matching, and order placement."""

    def __init__(
        self,
        config: AppConfig,
        profile_key: str,
        profile: ProfileConfig,
        state_path: Path,
    ):
        """Create a bot instance bound to one Tawreed profile and saved session state."""
        self.config = config
        self.profile_key = profile_key
        self.profile = profile
        self.state_path = state_path
        self.selectors = _selectors(config)
        self.skip_item_exception = _SkipItem

    def auth_interactive(self, wait_seconds: int = 600) -> None:
        """Open a visible browser and persist session state after manual login."""
        with sync_playwright() as p:
            browser, context, page = open_auth_page(p, self.config.base_url, self.config.runtime)
            attempt_env_login(page, self.selectors)
            print_auth_instructions(wait_seconds)
            detected = wait_for_login_detection(
                page,
                context,
                wait_seconds,
                self.selectors.logged_in_marker,
                self.state_path,
            )
            wait_for_network_idle(page)
            print_login_detection_result(detected)
            save_session_state(context, self.state_path, is_intermediate=False)
            browser.close()
            print(f"Saved session state: {self.state_path}")

    def place_order_from_items(self, items: list[Item]) -> None:
        """Place an order by processing each item from the provided list."""
        with sync_playwright() as p:
            browser, context, page = open_order_page(p, self.config.runtime, self.state_path)
            try:
                self._prepare_order_page(page)
                self._process_items(page, items)
                confirm_order(self, page)
            except Exception:
                dump_artifacts(page, self.profile_key, label="order_flow_error")
                raise
            finally:
                close_context(context)
                close_browser(browser)

    def _prepare_order_page(self, page: Page) -> None:
        """Open the site and navigate to the ordering surface for item processing."""
        page.goto(self._products_page_url(), wait_until="domcontentloaded")
        self._ensure_logged_in(page)
        maybe_switch_pharmacy(page, self.profile.pharmacy_switch or {})
        if self._order_surface_ready(page):
            return
        go_to_orders(page, self.selectors.go_to_orders, self._order_surface_selector())
        start_new_order(page, self.selectors.new_order, self.selectors.item_search_input)

    def _process_items(self, page: Page, items: list[Item]) -> None:
        """Process each requested Excel item on the current order page."""
        for item in items:
            self._process_single_item(page, item)

    def _order_surface_selector(self) -> str:
        """Return the selector that best indicates the order surface is ready."""
        if self.selectors.new_order:
            return self.selectors.new_order
        return self.selectors.item_search_input

    def _products_page_url(self) -> str:
        """Return the direct Tawreed products page URL for faster order startup."""
        if "#/" in self.config.base_url:
            origin, _ = self.config.base_url.split("#/", 1)
            return f"{origin}#/catalog/store-products/dv/"
        return self.config.base_url

    def _order_surface_ready(self, page: Page) -> bool:
        """Return whether the products ordering surface is already interactive."""
        try:
            page.locator(self.selectors.item_search_input).first.wait_for(timeout=1500)
            return True
        except Exception:
            return False

    def _process_single_item(self, page: Page, item: Item) -> None:
        """Add one item or save artifacts when a technical failure happens."""
        try:
            self._add_item(page, item)
        except _SkipItem as error:
            print(f"[{self.profile_key}] Skipped item {item.code} / {item.name}: {error}")
        except Exception as error:
            print(f"[{self.profile_key}] Failed item {item.code} / {item.name}: {error}")
            dump_artifacts(page, self.profile_key, label=f"item_error_{item.code or 'no_code'}")

    def _ensure_logged_in(self, page: Page) -> None:
        """Verify that the saved session is still authenticated before ordering begins."""
        ensure_logged_in(
            page,
            self.selectors,
            self.config.runtime.timeout_ms,
            ready_selector=self.selectors.item_search_input,
        )

    def _add_item(self, page: Page, item: Item) -> None:
        """Add one item using either the products-page flow or the legacy configured flow."""
        if self.selectors.item_search_input == "#tawreedTableGlobalSearch":
            add_item_from_products_page(self, page, item)
            return

        self._add_item_with_configured_flow(page, item)

    def _add_item_with_configured_flow(self, page: Page, item: Item) -> None:
        """Execute the selector-driven fallback flow for non-products ordering pages."""
        search = page.locator(self.selectors.item_search_input).first
        search.click()
        search.fill("")
        query = item.code if item.code else item.name
        search.fill(query)

        self._pick_configured_search_result(page, search)
        self._fill_configured_quantity(page, item.qty)
        page.locator(self.selectors.add_item_button).first.click()
        self._wait_for_legacy_add_completion(page)

    def _pick_configured_search_result(self, page: Page, search) -> None:
        """Select the configured search result when that selector exists."""
        if not self.selectors.item_first_result:
            return
        try:
            page.locator(self.selectors.item_first_result).first.wait_for(timeout=5000)
            page.locator(self.selectors.item_first_result).first.click()
        except Exception:
            search.press("Enter")

    def _fill_configured_quantity(self, page: Page, quantity: int) -> None:
        """Fill the configured quantity input when that selector exists."""
        if not self.selectors.qty_input:
            return
        quantity_input = page.locator(self.selectors.qty_input).first
        quantity_input.fill("")
        quantity_input.fill(str(quantity))

    def _pick_warehouse_if_needed(self, page: Page) -> None:
        """Pick a warehouse row from a warehouse chooser when that flow is active."""
        mode = self._warehouse_mode()
        rows = page.locator(self.selectors.warehouse_rows)
        if rows.count() == 0:
            return

        if mode == "first_available":
            self._click_warehouse_row(page, rows.first)
            return

        if mode == "max_available":
            row_index = max_available_warehouse_row(rows, self.selectors.warehouse_available_qty)
            self._click_warehouse_row(page, rows.nth(row_index))
            return

        raise ValueError(f"Unknown warehouse strategy mode: {mode}")

    def _warehouse_mode(self) -> str:
        """Return the configured warehouse-selection mode."""
        return str(self.config.warehouse_strategy.get("mode", "first_available"))

    def _click_warehouse_row(self, page: Page, row) -> None:
        """Click the warehouse pick button for the provided row."""
        row.locator(self.selectors.warehouse_pick_button).first.click()
        self._wait_for_warehouse_selection(page)

    def _wait_for_legacy_add_completion(self, page: Page) -> None:
        """Wait briefly for the legacy add-item flow to settle after submission."""
        try:
            page.locator(self.selectors.item_search_input).first.wait_for(timeout=1000)
        except Exception:
            pass

    def _wait_for_warehouse_selection(self, page: Page) -> None:
        """Wait briefly for the warehouse chooser to settle after selecting a row."""
        try:
            page.locator(self.selectors.warehouse_rows).first.wait_for(state="hidden", timeout=1000)
        except Exception:
            pass
