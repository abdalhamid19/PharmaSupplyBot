"""UI locator and dialog helpers for Tawreed Playwright automation."""

from __future__ import annotations

from playwright.sync_api import Page


def visible_dialog(page: Page, timeout_ms: int):
    """Return the top-most visible Tawreed dialog."""
    dialog = page.locator(".p-dialog:visible").last
    dialog.wait_for(timeout=timeout_ms)
    return dialog


def dialog_footer_buttons(dialog, timeout_ms: int):
    """Return footer buttons for the currently visible Tawreed dialog."""
    footer_buttons = dialog.locator(".p-dialog-footer button")
    footer_buttons.last.wait_for(timeout=timeout_ms)
    return footer_buttons


def bounded_requested_quantity(quantity_input, requested_quantity: int) -> int:
    """Clamp the requested quantity to the allowed quantity range in the dialog."""
    max_attr = quantity_input.get_attribute("aria-valuemax") or quantity_input.get_attribute("max") or "1"
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
    return scope.locator("button:has(.pi-building)").first


def cart_button(scope):
    """Return the cart button inside the provided scope."""
    return scope.locator("button:has(.pi-shopping-cart)").first


def store_dialog_cart_buttons(dialog):
    """Return all cart buttons rendered inside the stores dialog."""
    return dialog.locator(".p-dialog-content button:has(.pi-shopping-cart)")


def checkout_confirmation_labels() -> tuple[str, ...]:
    """Return the button labels accepted as checkout confirmation actions."""
    return (
        "Confirm",
        "confirm",
        "Ok",
        "OK",
        "Continue",
        "Yes",
        "Submit",
        "ØªØ£ÙƒÙŠØ¯",
        "Ù…ØªØ§Ø¨Ø¹Ø©",
        "Ù†Ø¹Ù…",
    )
