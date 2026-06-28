"""Add-to-cart dialog handling for Tawreed products flow."""

from playwright.sync_api import Page

from .tawreed_ui import fill_quantity_input, visible_dialog


def fill_add_to_cart_dialog(bot, page: Page, requested_qty: int) -> int:
    """Fill the quantity dialog and return the actually ordered amount."""
    dialog = visible_dialog(page, bot.config.runtime.timeout_ms)
    qty = fill_quantity_input(dialog, requested_qty)
    dialog.locator("button:has-text('إضافة')").click()
    dialog.wait_for(state="hidden")
    return qty
