"""Playwright automation for product search and Tawreed ordering."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

from playwright.sync_api import Page, sync_playwright

from ..core.cart_removal_items import CartRemovalItem
from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.matching_models import MatchDecision
from ..core.utils.excel import Item
from .selectors import _selectors
from .tawreed_artifacts import dump_artifacts
from .tawreed_cart_removal import remove_items_from_cart, resolve_cart_removal_targets
from .tawreed_checkout import confirm_order
from .tawreed_constants import PRODUCTS_PAGE_ROUTE
from .tawreed_dialogs import close_visible_dialogs, visible_overlay_diagnostics
from .tawreed_match_logs import OrderItemSummary, append_order_result_summary
from .tawreed_navigation import go_to_orders, maybe_switch_pharmacy, start_new_order
from .tawreed_products_flow import add_item_from_products_page
from .tawreed_session import (
    close_browser,
    close_context,
    ensure_logged_in,
    headless_auth_failure_message,
    open_order_page,
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
        stop_flag_path: Path | None = None,
        fast_search: bool = False,
        summary_label_suffix: str | None = None,
    ):
        """Create a bot instance bound to one Tawreed profile and saved session state."""
        self.config = config
        self.profile_key = profile_key
        self.profile = profile
        self.state_path = state_path
        self.debug_browser = debug_browser
        self.stop_flag_path = stop_flag_path
        self.fast_search = fast_search
        self.summary_label_suffix = summary_label_suffix
        self.selectors = _selectors(config)
        self.skip_item_exception = _SkipItem
        self.no_results_exception = _NoResultsItem
        self._reset_last_item_state()

    def log(self, message: str) -> None:
        """Print a profile-scoped diagnostic message."""
        print(_console_safe(f"[{self.profile_key}] {message}"))

    def _reset_last_item_state(self) -> None:
        """Reset internal state tracking for the next item to be processed."""
        self.last_match_decision: MatchDecision | None = None
        self.last_match_elapsed_seconds = 0.0
        self.last_searched_queries: list[str] = []
        self.last_selected_discount_percent = ""
        self.last_selected_store_name = ""
        self.last_ordered_total_qty = 0

    def auth_interactive(self, wait_seconds: int = 600) -> None:
        """Open a visible browser and persist session state after manual login."""
        self._auth(wait_seconds=wait_seconds, headless=False)

    def auth_headless(self, wait_seconds: int = 120) -> None:
        """Run a headless login attempt and persist session state when credentials succeed."""
        self._auth(wait_seconds=wait_seconds, headless=True)

    def _auth(self, wait_seconds: int, headless: bool) -> None:
        """Authenticate in either interactive or headless mode and save session state."""
        from .tawreed_session import perform_tawreed_auth

        perform_tawreed_auth(self, wait_seconds, headless)

    def _headless_auth_error(self) -> Exception:
        """Return the explicit auth failure used when hosted login never leaves the login page."""
        return RuntimeError(headless_auth_failure_message())

    def place_order_from_items(self, items: Iterable[Item]) -> None:
        """Place an order by processing each item from the provided iterable."""
        with sync_playwright() as p:
            browser, context, page = open_order_page(
                p,
                self.config.runtime,
                self.state_path,
                debug_browser=self.debug_browser,
            )
            try:
                self._run_order_session(page, items)
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

    def _run_order_session(self, page: Page, items: Iterable[Item]) -> None:
        """Prepare the page and process items within an active order session."""
        self._prepare_order_page(page)
        completed = self._process_items(page, items)
        if completed and not self._stop_requested():
            if not self.config.runtime.submit_order:
                print(
                    f"[{self.profile_key}] Items added to cart. "
                    "Final order submission is disabled for manual human review."
                )
                return
            confirm_order(page, self.selectors, self.config.runtime.timeout_ms)
        else:
            print(
                f"[{self.profile_key}] Stop requested or incomplete. Order confirmation skipped."
            )

    def remove_cart_items(self, items: Iterable[CartRemovalItem]) -> None:
        """Remove the requested items from Tawreed carts."""
        with sync_playwright() as p:
            browser, context, page = open_order_page(
                p,
                self.config.runtime,
                self.state_path,
                debug_browser=self.debug_browser,
            )
            try:
                self._prepare_order_page(page)
                targets = resolve_cart_removal_targets(self, page, items)
                self._prepare_cart_page(page)
                remove_items_from_cart(self, page, targets)
            except Exception as error:
                self._handle_removal_error(page, error)
                raise
            finally:
                close_context(context)
                close_browser(browser)

    def _handle_removal_error(self, page: Page, error: Exception) -> None:
        """Capture diagnostics for cart removal failures."""
        dump_artifacts(
            page,
            self.profile_key,
            label="cart_removal_error",
            details=_artifact_details("cart_removal_error", error),
        )

    def _prepare_cart_page(self, page: Page) -> None:
        """Open Tawreed's cart page for cart-removal processing."""
        page.goto(self._cart_page_url(), wait_until="domcontentloaded")
        ensure_logged_in(
            page,
            self.selectors,
            self.config.runtime.timeout_ms,
            ready_selector=self.selectors.cart_rows,
        )
        maybe_switch_pharmacy(page, self.profile.pharmacy_switch or {})
        try:
            page.locator(self.selectors.cart_rows).first.wait_for(timeout=3000)
        except Exception:
            pass

    def _cart_page_url(self) -> str:
        """Return the direct Tawreed cart page URL."""
        route = self.selectors.cart_route
        if "#/" in self.config.base_url and route.startswith("#/"):
            origin, _ = self.config.base_url.split("#/", 1)
            return f"{origin}{route}"
        return route or self.config.base_url

    def _prepare_order_page(self, page: Page) -> None:
        """Open the site and navigate to the ordering surface for item processing."""
        page.goto(self._products_page_url(), wait_until="domcontentloaded")
        self._ensure_logged_in(page)
        maybe_switch_pharmacy(page, self.profile.pharmacy_switch or {})
        if self._order_surface_ready(page):
            return
        go_to_orders(page, self.selectors.go_to_orders, self._order_surface_selector())
        start_new_order(
            page, self.selectors.new_order, self.selectors.item_search_input
        )

    def _process_items(self, page: Page, items: Iterable[Item]) -> bool:
        """Process each requested Excel item on the current order page."""
        added_any = False
        for item in items:
            if self._stop_requested():
                print(
                    f"[{self.profile_key}] Stop requested before item {item.code} / {item.name}."
                )
                return False
            added_any = self._process_single_item(page, item) or added_any
        return added_any

    def _stop_requested(self) -> bool:
        """Return whether an external stop request has been written for this run."""
        return bool(self.stop_flag_path and self.stop_flag_path.exists())

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

    def _process_single_item(self, page: Page, item: Item) -> bool:
        """Add one item or save artifacts when a technical failure happens."""
        started_at = time.perf_counter()
        self._reset_last_item_state()
        try:
            close_visible_dialogs(page)
            self._add_item(page, item)
            close_visible_dialogs(page)
            self._record_success(item, started_at)
            return True
        except _SkipItem as error:
            close_visible_dialogs(page)
            self._record_skip(item, error, started_at)
            return False
        except Exception as error:
            self._record_failure(page, item, error, started_at)
            return False

    def _record_success(self, item: Item, started_at: float) -> None:
        """Record a successful add-to-cart summary."""
        self._record_item_summary(
            item,
            status="added-to-cart",
            reason="Added to cart.",
            elapsed_seconds=time.perf_counter() - started_at,
            match_elapsed_seconds=self.last_match_elapsed_seconds,
        )

    def _record_skip(self, item: Item, error: _SkipItem, started_at: float) -> None:
        """Record a skipped item summary."""
        reason = str(error)
        self._record_item_summary(
            item,
            status=self._skip_status(reason),
            reason=reason,
            elapsed_seconds=time.perf_counter() - started_at,
            match_elapsed_seconds=self.last_match_elapsed_seconds,
        )
        print(
            _console_safe(
                f"[{self.profile_key}] Skipped item {item.code} / {item.name}: {error}"
            )
        )

    def _record_failure(
        self, page: Page, item: Item, error: Exception, started_at: float
    ) -> None:
        """Record a technical failure and capture diagnostic artifacts."""
        reason = str(error)
        close_visible_dialogs(page)
        self._record_failure_summary(item, reason, started_at)
        self._print_failed_item(item, error)
        dump_artifacts(
            page,
            self.profile_key,
            label=_item_error_label(item),
            details=_item_error_details(page, item, error),
        )

    def _record_failure_summary(
        self, item: Item, reason: str, started_at: float
    ) -> None:
        """Append the summary row for one failed item."""
        self._record_item_summary(
            item,
            self._failure_status(reason),
            reason,
            time.perf_counter() - started_at,
            self.last_match_elapsed_seconds,
        )

    def _print_failed_item(self, item: Item, error: Exception) -> None:
        """Print one console-safe failed item message."""
        message = f"[{self.profile_key}] Failed item {item.code} / {item.name}: {error}"
        print(_console_safe(message))

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
        self.last_ordered_total_qty = int(item.qty)
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
            row_index = max_available_warehouse_row(
                rows, self.selectors.warehouse_available_qty
            )
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
            page.locator(self.selectors.warehouse_rows).first.wait_for(
                state="hidden", timeout=1000
            )
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
        summary = self._build_item_summary(
            status, reason, elapsed_seconds, match_elapsed_seconds
        )
        append_order_result_summary(
            self.profile_key, item, summary, label_suffix=self.summary_label_suffix
        )

    def _build_item_summary(
        self, status: str, reason: str, elapsed: float, match_elapsed: float
    ) -> OrderItemSummary:
        """Build a compact summary object from the current bot state."""
        return OrderItemSummary(
            status=status,
            reason=reason,
            ordered_total_qty=self.last_ordered_total_qty,
            **self._matched_summary_name_fields(),
            selected_discount_percent=self.last_selected_discount_percent,
            selected_store_name=self.last_selected_store_name,
            searched_queries_count=len(self.last_searched_queries),
            searched_queries=" | ".join(self.last_searched_queries),
            elapsed_seconds=elapsed,
            match_elapsed_seconds=match_elapsed,
        )

    def _matched_summary_name_fields(self) -> dict[str, str]:
        """Return named OrderItemSummary fields for the last matched product."""
        matched_name, english_name, arabic_name, matched_query = (
            self._matched_summary_fields()
        )
        return {
            "matched_product_name": matched_name,
            "matched_product_english_name": english_name,
            "matched_product_arabic_name": arabic_name,
            "matched_query": matched_query,
        }

    def _matched_summary_fields(self) -> tuple[str, str, str, str]:
        """Return matched product summary fields from the last recorded match decision."""
        decision = self.last_match_decision
        if not decision or not decision.best_match:
            return "", "", "", ""
        candidate = decision.best_match.data
        english_name = str(candidate.get("productNameEn") or "")
        arabic_name = str(candidate.get("productName") or "")
        product_name = english_name or arabic_name
        return product_name, english_name, arabic_name, decision.best_match.query

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


def _item_error_label(item: Item) -> str:
    """Return the artifact label for one failed item."""
    return f"item_error_{item.code or 'no_code'}"


def _item_error_details(page: Page, item: Item, error: Exception) -> str:
    """Build diagnostic artifact details for one failed item."""
    return _artifact_details(
        _item_error_label(item),
        error,
        overlay_diagnostics=visible_overlay_diagnostics(page),
        item_code=item.code,
        item_name=item.name,
        item_qty=item.qty,
    )


def _artifact_details(label: str, error: Exception, **extra: object) -> str:
    """Build plain-text diagnostic details for saved failure artifacts."""
    lines = [f"label={label}", f"error_type={type(error).__name__}", f"error={error}"]
    for key, value in extra.items():
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _console_safe(text: str) -> str:
    """Return text that can be printed on cp1252 Windows consoles without crashing."""
    return text.encode("cp1252", errors="replace").decode("cp1252")
