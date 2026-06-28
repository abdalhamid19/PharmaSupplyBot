"""Tawreed cart flow management."""

from __future__ import annotations

from typing import Iterable

from playwright.sync_api import Page, sync_playwright

from ..core.cart_removal_items import CartRemovalItem
from .tawreed_api_contract import begin_api_contract_capture, save_api_contract_capture
from .tawreed_cart_removal import remove_items_from_cart, resolve_cart_removal_targets
from .tawreed_navigation import maybe_switch_pharmacy
from .tawreed_session import close_browser, close_context, ensure_logged_in, open_order_page


class TawreedCartFlow:
    """Handles Tawreed cart operations."""

    def __init__(self, bot):
        """Initialize cart flow with bot instance."""
        self.bot = bot

    def remove_cart_items(self, items: Iterable[CartRemovalItem]) -> None:
        """Remove the requested items from Tawreed carts."""
        self.bot._ensure_valid_auth()
        items = list(items)
        if self.bot._try_api_cart_removal(items):
            return
        with sync_playwright() as p:
            browser, context, page = open_order_page(
                p,
                self.bot.config.runtime,
                self.bot.state_path,
                debug_browser=self.bot.debug_browser,
            )
            api_capture = begin_api_contract_capture(page)
            try:
                self._prepare_order_page(page)
                targets = resolve_cart_removal_targets(self.bot, page, items)
                self._prepare_cart_page(page)
                remove_items_from_cart(self.bot, page, targets)
            except Exception as error:
                self._handle_removal_error(page, error)
                raise
            finally:
                _save_api_contract_capture(api_capture)
                close_context(context)
                close_browser(browser)

    def _handle_removal_error(self, page: Page, error: Exception) -> None:
        """Capture diagnostics for cart removal failures."""
        from .tawreed_artifacts import dump_artifacts
        from .tawreed_order_flow import _artifact_details

        dump_artifacts(
            page,
            self.bot.profile_key,
            label="cart_removal_error",
            details=_artifact_details("cart_removal_error", error),
        )

    def _prepare_cart_page(self, page: Page) -> None:
        """Open Tawreed's cart page for cart-removal processing."""
        page.goto(self._cart_page_url(), wait_until="domcontentloaded")
        ensure_logged_in(
            page,
            self.bot.selectors,
            self.bot.config.runtime.timeout_ms,
            ready_selector=self.bot.selectors.cart_rows,
        )
        maybe_switch_pharmacy(page, self.bot.profile.pharmacy_switch or {})
        try:
            page.locator(self.bot.selectors.cart_rows).first.wait_for(timeout=3000)
        except Exception:
            pass

    def _cart_page_url(self) -> str:
        """Return the direct Tawreed cart page URL."""
        route = self.bot.selectors.cart_route
        if "#/" in self.bot.config.base_url and route.startswith("#/"):
            origin, _ = self.bot.config.base_url.split("#/", 1)
            return f"{origin}{route}"
        return route or self.bot.config.base_url

    def _prepare_order_page(self, page: Page) -> None:
        """Open the site and navigate to the ordering surface for item processing."""
        page.goto(self.bot._products_page_url(), wait_until="domcontentloaded")
        self._ensure_logged_in(page)
        maybe_switch_pharmacy(page, self.bot.profile.pharmacy_switch or {})

    def _ensure_logged_in(self, page: Page) -> None:
        """Verify that the saved session is still authenticated before ordering begins."""
        ensure_logged_in(
            page,
            self.bot.selectors,
            self.bot.config.runtime.timeout_ms,
            ready_selector=self.bot.selectors.item_search_input,
        )


def _save_api_contract_capture(captured: list[dict]) -> None:
    try:
        save_api_contract_capture(captured)
    except Exception:
        pass
