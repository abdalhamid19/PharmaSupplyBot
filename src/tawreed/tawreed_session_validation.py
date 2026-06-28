"""Session validation logic for Tawreed authentication."""

from playwright.sync_api import Page

from .tawreed_session_auth import SessionInvalidError
from .tawreed_session_browser import open_order_page, close_context, close_browser


def _is_logged_in_marker_visible(page: Page, logged_in_marker: str, timeout_ms: int) -> bool:
    """Return whether the configured logged-in marker appears within the timeout."""
    from .tawreed_auth_waits import is_logged_in_marker_visible
    return is_logged_in_marker_visible(page, logged_in_marker, timeout_ms)


def _has_logged_in_marker(page: Page, logged_in_marker: str, timeout_ms: int) -> bool:
    """Return whether the configured logged-in marker is visible."""
    return _is_logged_in_marker_visible(page, logged_in_marker, timeout_ms)


def _is_login_form_visible(page: Page, selectors) -> bool:
    """Return whether the login form is still visible on the current page."""
    try:
        login_email_visible = page.locator(selectors.login_email).first.is_visible(timeout=2000)
        login_password_visible = page.locator(
            selectors.login_password
        ).first.is_visible(timeout=2000)
        return bool(login_email_visible or login_password_visible)
    except Exception:
        return False


def _ready_surface_visible(
    page: Page, ready_selector: str, timeout_ms: int = 1200
) -> bool:
    """Return whether the requested page surface is already interactive."""
    if not ready_selector:
        return False
    try:
        page.locator(ready_selector).first.wait_for(timeout=timeout_ms)
        return True
    except Exception:
        return False


def validate_saved_session(
    playwright,
    runtime,
    state_path,
    target_url: str,
    selectors,
    ready_selector: str,
) -> None:
    """Open a fresh browser context with one saved state and verify it is authenticated."""
    browser, context, page = open_order_page(playwright, runtime, state_path)
    try:
        page.goto(target_url, wait_until="domcontentloaded")
        ensure_logged_in(page, selectors, runtime.timeout_ms, ready_selector=ready_selector)
    finally:
        close_context(context)
        close_browser(browser)


def ensure_logged_in(page: Page, selectors, timeout_ms: int, ready_selector: str = "") -> None:
    """Verify that the saved session is still authenticated."""
    page.wait_for_load_state("domcontentloaded")
    if _ready_surface_visible(page, ready_selector): return
    if _is_login_form_visible(page, selectors):
        raise SessionInvalidError("Saved session is expired or on login page.")
    if _ready_surface_visible(page, ready_selector, min(timeout_ms, 15000)): return
    if _has_logged_in_marker(page, selectors.logged_in_marker, min(timeout_ms, 2000)):
        return
    if _ready_surface_visible(page, ready_selector, min(timeout_ms, 15000)): return
    if _is_login_form_visible(page, selectors):
        raise SessionInvalidError("Saved session is expired or on login page.")
    raise SessionInvalidError("Saved session did not expose order surface.")


def _is_logged_in_marker_visible(page: Page, logged_in_marker: str, timeout_ms: int) -> bool:
    """Return whether the configured logged-in marker appears within the timeout."""
    from .tawreed_auth_waits import is_logged_in_marker_visible
    return is_logged_in_marker_visible(page, logged_in_marker, timeout_ms)


def _has_logged_in_marker(page: Page, logged_in_marker: str, timeout_ms: int) -> bool:
    """Return whether the configured logged-in marker is visible."""
    return _is_logged_in_marker_visible(page, logged_in_marker, timeout_ms)


def _is_login_form_visible(page: Page, selectors) -> bool:
    """Return whether the login form is still visible on the current page."""
    try:
        login_email_visible = page.locator(selectors.login_email).first.is_visible(timeout=2000)
        login_password_visible = page.locator(
            selectors.login_password
        ).first.is_visible(timeout=2000)
        return bool(login_email_visible or login_password_visible)
    except Exception:
        return False


def _ready_surface_visible(
    page: Page, ready_selector: str, timeout_ms: int = 1200
) -> bool:
    """Return whether the requested page surface is already interactive."""
    if not ready_selector:
        return False
    try:
        page.locator(ready_selector).first.wait_for(timeout=timeout_ms)
        return True
    except Exception:
        return False
