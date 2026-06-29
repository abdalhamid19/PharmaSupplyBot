"""Checkout and order confirmation flow for Tawreed."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

def confirm_order(page: Page, selectors, timeout_ms: int) -> None:
    """Navigate through the checkout screens and submit the final order."""
    page.locator(selectors.checkout_button).click()
    page.wait_for_load_state("networkidle", timeout=timeout_ms)
    _submit_final(page, selectors, timeout_ms)

def _submit_final(page, selectors, timeout_ms):
    """Click the final confirmation button."""
    page.locator(selectors.confirm_order_button).click()
    page.wait_for_load_state("networkidle", timeout=timeout_ms)
