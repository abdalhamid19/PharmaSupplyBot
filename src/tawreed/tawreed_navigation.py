"""Navigation helpers for reaching Tawreed ordering pages."""

from __future__ import annotations

from playwright.sync_api import Page


def maybe_switch_pharmacy(page: Page, pharmacy_switch_settings: dict) -> None:
    """Switch the active pharmacy when the profile explicitly enables that step."""
    if not pharmacy_switch_settings.get("enabled"):
        return
    pharmacy_name = str(pharmacy_switch_settings.get("pharmacy_name", "")).strip()
    if not pharmacy_name:
        return
    page.get_by_text(pharmacy_name, exact=False).first.click(timeout=3000)


def go_to_orders(page: Page, go_to_orders_selector: str, ready_selector: str) -> None:
    """Navigate from the landing page to the products ordering page."""
    try:
        page.locator(go_to_orders_selector).first.click()
    except Exception:
        open_products_link_fallback(page)
    _wait_for_ready_selector(page, ready_selector)


def open_products_link_fallback(page: Page) -> None:
    """Use visible sidebar labels when the configured navigation selector fails."""
    try:
        page.get_by_role("link", name="Products").first.click()
    except Exception:
        try:
            page.get_by_text("Products", exact=False).first.click()
        except Exception:
            page.get_by_text("المنتجات", exact=False).first.click()


def start_new_order(page: Page, new_order_selector: str, ready_selector: str) -> None:
    """Open the new-order surface when the current flow requires that step."""
    if not new_order_selector:
        return
    page.locator(new_order_selector).first.click()
    _wait_for_ready_selector(page, ready_selector)


def _wait_for_ready_selector(page: Page, ready_selector: str) -> None:
    """Wait for the next page surface to expose its primary ready selector."""
    if not ready_selector:
        return
    try:
        page.locator(ready_selector).first.wait_for(timeout=2000)
    except Exception:
        pass
