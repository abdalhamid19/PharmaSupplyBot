"""Login-detection signals used during interactive Tawreed auth."""

from __future__ import annotations

from playwright.sync_api import Page


def login_detected(
    page: Page,
    timeout_ms: int,
    login_email_selector: str,
    login_password_selector: str,
    logged_in_marker: str,
) -> bool:
    """Return whether any reliable post-login signal appears within the timeout."""
    return any(
        [
            is_logged_in_marker_visible(page, logged_in_marker, timeout_ms),
            login_form_disappeared(page, login_email_selector, login_password_selector),
            left_login_route(page),
        ]
    )


def is_logged_in_marker_visible(page: Page, logged_in_marker: str, timeout_ms: int) -> bool:
    """Return whether the configured logged-in marker appears within the timeout."""
    try:
        page.locator(logged_in_marker).first.wait_for(timeout=timeout_ms)
        return True
    except Exception:
        return False


def login_form_disappeared(
    page: Page,
    login_email_selector: str,
    login_password_selector: str,
) -> bool:
    """Return whether the login form is no longer visible on the current page."""
    return not any(
        [
            selector_visible(page, login_email_selector),
            selector_visible(page, login_password_selector),
        ]
    )


def left_login_route(page: Page) -> bool:
    """Return whether the browser has moved away from the Tawreed login route."""
    return "#/login" not in page.url.lower()


def selector_visible(page: Page, selector: str) -> bool:
    """Return whether one selector is visible without failing the auth poll."""
    if not selector:
        return False
    try:
        return bool(page.locator(selector).first.is_visible(timeout=250))
    except Exception:
        return False
