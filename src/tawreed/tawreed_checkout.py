"""Checkout helpers for Tawreed order confirmation."""

from __future__ import annotations

from playwright.sync_api import Page

from .tawreed_constants import ENABLED_CHECKOUT_TEXT_SELECTOR, VISIBLE_DIALOG_SELECTOR
from .tawreed_ui import checkout_confirmation_labels


def confirm_order(bot, page: Page) -> None:
    """Click enabled checkout buttons and confirm resulting dialogs."""
    if not bot.config.runtime.submit_order:
        print(
            f"[{bot.profile_key}] Order submission skipped. "
            "Items were prepared for manual human review."
        )
        return
    if not bot.selectors.confirm_order_button:
        return
    checkout_buttons = _checkout_candidates(bot, page)
    checkout_count = checkout_buttons.count()
    if checkout_count == 0:
        _print_no_checkout_buttons_message(bot)
        return
    for checkout_index in range(checkout_count):
        button = checkout_buttons.nth(checkout_index)
        try:
            _click_checkout_button(bot, button, page)
            _confirm_checkout_dialog(page)
        except Exception as error:
            _print_checkout_failure(bot, checkout_index, checkout_count, error)


def _checkout_candidates(bot, page: Page):
    """Return checkout buttons that appear to be enabled for submission."""
    configured_buttons = page.locator(bot.selectors.confirm_order_button)
    enabled_buttons = configured_buttons.filter(has_not=page.locator("[disabled]"))
    enabled_checkout_text = page.locator(ENABLED_CHECKOUT_TEXT_SELECTOR)
    if enabled_checkout_text.count() > 0:
        return enabled_checkout_text
    return enabled_buttons


def _print_no_checkout_buttons_message(bot) -> None:
    """Print the message used when no checkout button is currently actionable."""
    print(
        f"[{bot.profile_key}] No enabled Checkout buttons found "
        "(cart may be empty, out of stock, or below minimum order)."
    )


def _click_checkout_button(bot, button, page: Page) -> None:
    """Click a checkout button, retrying with force if overlays intercept it."""
    try:
        button.click(timeout=5000)
    except Exception:
        button.click(timeout=5000, force=True)
    _wait_for_checkout_dialog(page)


def _confirm_checkout_dialog(page: Page) -> None:
    """Confirm the visible checkout dialog using known multilingual labels."""
    dialog = _visible_checkout_dialog(page)
    if dialog.count() == 0:
        return
    for label in checkout_confirmation_labels():
        confirm_button = dialog.locator(f"button:has-text('{label}')")
        if confirm_button.count() == 0:
            continue
        try:
            confirm_button.first.click(timeout=3000)
            _wait_for_checkout_completion(dialog, page)
            return
        except Exception:
            pass


def _wait_for_checkout_dialog(page: Page) -> None:
    """Wait briefly for a checkout confirmation dialog to appear."""
    try:
        _visible_checkout_dialog(page).first.wait_for(timeout=1200)
    except Exception:
        pass


def _visible_checkout_dialog(page: Page):
    """Return the visible checkout dialog locator."""
    return page.locator(VISIBLE_DIALOG_SELECTOR)


def _wait_for_checkout_completion(dialog, page: Page) -> None:
    """Wait for the checkout confirmation dialog to close after submission."""
    try:
        dialog.first.wait_for(state="hidden", timeout=1500)
        return
    except Exception:
        pass
    try:
        page.wait_for_load_state("domcontentloaded", timeout=1000)
    except Exception:
        pass


def _print_checkout_failure(
    bot,
    checkout_index: int,
    checkout_count: int,
    error: Exception,
) -> None:
    """Print the message used when one checkout click attempt fails."""
    print(
        f"[{bot.profile_key}] Checkout click failed on button "
        f"{checkout_index + 1}/{checkout_count}: {error}"
    )
