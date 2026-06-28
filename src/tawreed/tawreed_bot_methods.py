"""Other TawreedBot methods (auth, flow delegation, utilities)."""

from __future__ import annotations

from typing import Iterable

from ..core.cart_removal_items import CartRemovalItem
from ..core.utils.excel import Item
from .tawreed_constants import PRODUCTS_PAGE_ROUTE


class TawreedBotMethods:
    """Other TawreedBot methods (auth, flow delegation, utilities)."""

    def _ensure_valid_auth(self) -> None:
        """Verify token is valid or refresh authentication automatically."""
        self.auth_flow.ensure_valid_auth()

    def auth_interactive(self, wait_seconds: int = 600) -> None:
        """Open a visible browser and persist session state after manual login."""
        self.auth_flow.auth_interactive(wait_seconds)

    def auth_headless(self, wait_seconds: int = 120) -> None:
        """Run a headless login attempt and persist session state when credentials succeed."""
        self.auth_flow.auth_headless(wait_seconds)

    def _headless_auth_error(self) -> Exception:
        """Return the explicit auth failure used when hosted login never leaves the login page."""
        return self.auth_flow._headless_auth_error()

    def place_order_from_items(self, items: Iterable[Item]) -> None:
        """Place an order by processing each item from the provided iterable."""
        self.order_flow.place_order_from_items(items)

    def match_items_only(self, items: Iterable[Item]) -> None:
        """Match Tawreed products for each item without adding anything to the cart."""
        self.order_flow.match_items_only(items)

    def remove_cart_items(self, items: Iterable[CartRemovalItem]) -> None:
        """Remove the requested items from Tawreed carts."""
        self.cart_flow.remove_cart_items(items)

    def _stop_before_item(self, item: Item) -> bool:
        """Return True and print a diagnostic when a run should stop before an item."""
        if not self._stop_requested():
            return False
        print(
            f"[{self.profile_key}] Stop requested before item {item.code} / {item.name}."
        )
        return True

    def _stop_requested(self) -> bool:
        """Return whether an external stop request has been written for this run."""
        return bool(self.stop_flag_path and self.stop_flag_path.exists())

    def _products_page_url(self) -> str:
        """Return the direct Tawreed products page URL for faster order startup."""
        if "#/" in self.config.base_url:
            origin, _ = self.config.base_url.split("#/", 1)
            return f"{origin}{PRODUCTS_PAGE_ROUTE}"
        return self.config.base_url

    def _record_pending_item_timing(self, key: str, elapsed_seconds: float) -> None:
        """Attach one setup timing bucket to the next processed item."""
        pending = getattr(self, "_pending_item_timings", {})
        pending[key] = float(pending.get(key, 0.0)) + max(0.0, float(elapsed_seconds))
        self._pending_item_timings = pending

    # Delegation methods for backward compatibility with tests
    def _skip_status(self, reason: str) -> str:
        """Return the structured summary status for one skipped item."""
        return self.order_flow._skip_status(reason)

    def _build_item_summary(self, status: str, reason: str, elapsed: float, match_elapsed: float):
        """Build a compact summary object from the current bot state."""
        return self.order_flow._build_item_summary(status, reason, elapsed, match_elapsed)

    def _order_surface_ready(self, page) -> bool:
        """Return whether the products ordering surface is already interactive."""
        return self.order_flow._order_surface_ready(page)

    def _process_single_item(self, page, item):
        """Add one item or save artifacts when a technical failure happens."""
        return self.order_flow._process_single_item(page, item)

    def _process_single_match_only_item(self, page, item):
        """Match one item without running any add-to-cart action."""
        return self.order_flow._process_single_match_only_item(page, item)

    def _prepare_order_page(self, page):
        """Open the site and navigate to the ordering surface for item processing."""
        return self.order_flow._prepare_order_page(page)

    def _process_items(self, page, items):
        """Process each requested Excel item on the current order page."""
        return self.order_flow._process_items(page, items)

    def _is_products_page(self, page):
        """Return whether the current page is Tawreed's products ordering page."""
        return self.order_flow._is_products_page(page)

    def _record_item_summary(self, item, status, reason, elapsed_seconds, match_elapsed_seconds):
        """Append one execution-summary row for the processed item."""
        return self.order_flow._record_item_summary(item, status, reason, elapsed_seconds, match_elapsed_seconds)

    def _match_item_only(self, page, item):
        """Run Tawreed matching for one item without opening the cart dialog."""
        return self.order_flow._match_item_only(page, item)

    def _run_match_only_session(self, page, items):
        """Prepare Tawreed and process item matching without cart actions."""
        return self.order_flow._run_match_only_session(page, items)

    def _add_item(self, page, item):
        """Add one item using either the products-page flow or the legacy configured flow."""
        return self.order_flow._add_item(page, item)
