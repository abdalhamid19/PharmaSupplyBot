"""Playwright automation for product search and Tawreed ordering."""

from __future__ import annotations

from pathlib import Path
import time

from playwright.sync_api import Page, sync_playwright

from .config_models import AppConfig, ProfileConfig
from .excel import Item
from .selectors import _selectors
from .tawreed_artifacts import dump_artifacts
from .tawreed_checkout import confirm_order
from .tawreed_constants import PRODUCTS_PAGE_ROUTE
from .tawreed_match_logs import OrderItemSummary, append_order_result_summary
from .tawreed_navigation import go_to_orders, maybe_switch_pharmacy, start_new_order
from .tawreed_products_flow import add_item_from_products_page, close_visible_dialogs
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


class _NoResultsItem(_SkipItem):
    """Signal that one item had no Tawreed results and should be skipped quickly."""

    pass


class TawreedBot:
    """Coordinate Tawreed authentication, product matching, and order placement."""

    def __init__(
        self,
        config: AppConfig,
        profile_key: str,
        profile: ProfileConfig,
        state_path: Path,
        debug_browser: bool = False,
    ):
        """Create a bot instance bound to one Tawreed profile and saved session state."""
        self.config = config
        self.profile_key = profile_key
        self.profile = profile
        self.state_path = state_path
        self.debug_browser = debug_browser
        self.selectors = _selectors(config)
        self.skip_item_exception = _SkipItem
        self.no_results_exception = _NoResultsItem
        self.last_match_decision = None
        self.last_match_elapsed_seconds = 0.0
        self.last_searched_queries: list[str] = []

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
            browser, context, page = open_order_page(
                p,
                self.config.runtime,
                self.state_path,
                debug_browser=self.debug_browser,
            )
            try:
                self._prepare_order_page(page)
                self._process_items(page, items)
                confirm_order(self, page)
            except Exception as error:
                dump_artifacts(
                    page,
                    self.profile_key,
                    label="order_flow_error",
                    details=_artifact_details("order_flow_error", error),
                )
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
            return f"{origin}{PRODUCTS_PAGE_ROUTE}"
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
        started_at = time.perf_counter()
        self.last_match_decision = None
        self.last_match_elapsed_seconds = 0.0
        self.last_searched_queries = []
        try:
            close_visible_dialogs(page)
            self._add_item(page, item)
            close_visible_dialogs(page)
            self._record_item_summary(
                item,
                status="added-to-cart",
                reason="Added to cart.",
                elapsed_seconds=time.perf_counter() - started_at,
                match_elapsed_seconds=self.last_match_elapsed_seconds,
            )
        except _SkipItem as error:
            close_visible_dialogs(page)
            self._record_item_summary(
                item,
                status=self._skip_status(str(error)),
                reason=str(error),
                elapsed_seconds=time.perf_counter() - started_at,
                match_elapsed_seconds=self.last_match_elapsed_seconds,
            )
            print(_console_safe(f"[{self.profile_key}] Skipped item {item.code} / {item.name}: {error}"))
        except Exception as error:
            close_visible_dialogs(page)
            self._record_item_summary(
                item,
                status=self._failure_status(str(error)),
                reason=str(error),
                elapsed_seconds=time.perf_counter() - started_at,
                match_elapsed_seconds=self.last_match_elapsed_seconds,
            )
            print(_console_safe(f"[{self.profile_key}] Failed item {item.code} / {item.name}: {error}"))
            dump_artifacts(
                page,
                self.profile_key,
                label=f"item_error_{item.code or 'no_code'}",
                details=_artifact_details(
                    f"item_error_{item.code or 'no_code'}",
                    error,
                    item_code=item.code,
                    item_name=item.name,
                    item_qty=item.qty,
                ),
            )

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
        if self._is_products_page(page):
            add_item_from_products_page(self, page, item)
            return

        self._add_item_with_configured_flow(page, item)

    def _is_products_page(self, page: Page) -> bool:
        """Return whether the current page is Tawreed's products ordering page."""
        return PRODUCTS_PAGE_ROUTE in page.url

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

    def _record_item_summary(
        self,
        item: Item,
        status: str,
        reason: str,
        elapsed_seconds: float,
        match_elapsed_seconds: float,
    ) -> None:
        """Append one execution-summary row for the processed item."""
        matched_product_name, matched_query = self._matched_summary_fields()
        append_order_result_summary(
            self.profile_key,
            item,
            OrderItemSummary(
                status=status,
                reason=reason,
                matched_product_name=matched_product_name,
                matched_query=matched_query,
                searched_queries_count=len(self.last_searched_queries),
                searched_queries=" | ".join(self.last_searched_queries),
                elapsed_seconds=elapsed_seconds,
                match_elapsed_seconds=match_elapsed_seconds,
            ),
        )

    def _matched_summary_fields(self) -> tuple[str, str]:
        """Return matched product summary fields from the last recorded match decision."""
        decision = self.last_match_decision
        if not decision or not decision.best_match:
            return "", ""
        candidate = decision.best_match.data
        product_name = str(candidate.get("productNameEn") or candidate.get("productName") or "")
        return product_name, decision.best_match.query

    def _skip_status(self, reason: str) -> str:
        """Return the structured summary status for one skipped item."""
        lowered = reason.lower()
        if "no matching product found" in lowered:
            return "no-results"
        if "unavailable" in lowered or "out of stock" in lowered:
            return "matched-but-unavailable"
        return "skipped"

    def _failure_status(self, reason: str) -> str:
        """Return the structured summary status for one failed item."""
        if "No matching product found" in reason:
            return "no-results"
        return "failed"


def _artifact_details(label: str, error: Exception, **extra: object) -> str:
    """Build plain-text diagnostic details for saved failure artifacts."""
    lines = [f"label={label}", f"error_type={type(error).__name__}", f"error={error}"]
    for key, value in extra.items():
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _console_safe(text: str) -> str:
    """Return text that can be printed on cp1252 Windows consoles without crashing."""
    return text.encode("cp1252", errors="replace").decode("cp1252")
