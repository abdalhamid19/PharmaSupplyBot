"""UI locator and dialog helpers for Tawreed Playwright automation."""

from __future__ import annotations

from playwright.sync_api import Page

from .tawreed_constants import (
    CART_BUTTON_SELECTOR,
    CHECKOUT_CONFIRMATION_LABELS,
    DIALOG_MASK_SELECTOR,
    DIALOG_FOOTER_BUTTONS_SELECTOR,
    OVERLAY_PANEL_SELECTOR,
    STORE_DIALOG_CLOSE_BUTTON_SELECTOR,
    STORE_DIALOG_ROWS_SELECTOR,
    STORE_DIALOG_CART_BUTTONS_SELECTOR,
    STORES_BUTTON_SELECTOR,
    VISIBLE_DIALOG_SELECTOR,
)


def visible_dialog(page: Page, timeout_ms: int):
    """Return the top-most visible Tawreed dialog."""
    dialog = page.locator(VISIBLE_DIALOG_SELECTOR).last
    dialog.wait_for(timeout=timeout_ms)
    return dialog


def dialog_footer_buttons(dialog, timeout_ms: int):
    """Return footer buttons for the currently visible Tawreed dialog."""
    footer_buttons = dialog.locator(DIALOG_FOOTER_BUTTONS_SELECTOR)
    footer_buttons.last.wait_for(timeout=timeout_ms)
    return footer_buttons


def bounded_requested_quantity(quantity_input, requested_quantity: int) -> int:
    """Clamp the requested quantity to the allowed quantity range in the dialog."""
    max_attr = (
        quantity_input.get_attribute("aria-valuemax")
        or quantity_input.get_attribute("max")
        or "1"
    )
    try:
        max_quantity = max(1, int(float(max_attr)))
    except Exception:
        max_quantity = 1
    return max(1, min(int(requested_quantity), max_quantity))


def fill_quantity_input(quantity_input, quantity: int) -> None:
    """Fill the quantity input with the validated quantity value."""
    quantity_input.click()
    quantity_input.fill("")
    quantity_input.type(str(quantity), delay=10)


def stores_button(scope):
    """Return the stores button inside the provided scope."""
    return scope.locator(STORES_BUTTON_SELECTOR).first


def cart_button(scope):
    """Return the cart button inside the provided scope."""
    return scope.locator(CART_BUTTON_SELECTOR).first


def store_dialog_cart_buttons(dialog):
    """Return all cart buttons rendered inside the stores dialog."""
    return dialog.locator(STORE_DIALOG_CART_BUTTONS_SELECTOR)


def dialog_close_buttons(dialog):
    """Return the close buttons rendered for the current dialog."""
    return dialog.locator(STORE_DIALOG_CLOSE_BUTTON_SELECTOR)


def store_dialog_rows(dialog):
    """Return the visible data rows inside the stores dialog."""
    return dialog.locator(STORE_DIALOG_ROWS_SELECTOR)


def visible_dialog_masks(page: Page):
    """Return the visible Tawreed dialog masks."""
    return page.locator(f"{DIALOG_MASK_SELECTOR}:visible")


def visible_overlay_panels(page: Page):
    """Return visible non-dialog overlay panels that can block the products page."""
    return page.locator(_visible_selector(OVERLAY_PANEL_SELECTOR))


def checkout_confirmation_labels() -> tuple[str, ...]:
    """Return the button labels accepted as checkout confirmation actions."""
    return CHECKOUT_CONFIRMATION_LABELS


def _visible_selector(selector: str) -> str:
    """Add :visible to each selector in a comma-separated selector list."""
    return ", ".join(f"{part.strip()}:visible" for part in selector.split(",") if part.strip())
