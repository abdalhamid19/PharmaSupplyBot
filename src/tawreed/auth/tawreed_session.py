"""Session management for Tawreed authentication - unified module."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from playwright.sync_api import Page

from ..tawreed_login_detection import is_logged_in_marker_visible
from ..tawreed_playwright_browser import launch_chromium
from .tawreed_auth import headless_auth_failure_message
from .tawreed_session_state import (
    auth_temp_state_path,
    save_session_state,
    promote_session_state,
    discard_session_state,
    wait_for_login_detection,
)
from .tawreed_session_auth import (
    SessionInvalidError,
    attempt_env_login,
    print_auth_instructions,
    print_login_detection_result,
    wait_for_network_idle,
    perform_tawreed_auth,
)


# ============================================================================
# Browser operations
# ============================================================================

# Navigations target a remote SPA over the public internet; the widget-level
# default timeout (state/config.yaml timeout_ms, commonly 15000) is too tight
# for cold TCP/TLS handshakes. A transient first-connection stall of 20+ s was
# observed in the field (TCP connect to seller.tawreed.io took 21 s once, then
# 0.05 s on retry), so navigations get a floor plus one retry on timeout.
NAVIGATION_TIMEOUT_FLOOR_MS = 60_000


def resilient_goto(page, url: str, timeout_ms: int | None = None) -> None:
    """Navigate with a navigation-grade timeout and one retry on timeout.

    Playwright raises TimeoutError when a page load exceeds the timeout; one
    retry absorbs transient network stalls (cold TLS, DNS hiccup) without
    masking persistent failures (the retry must succeed or the error raises).
    The effective timeout is the requested/default value raised to a
    navigation-grade floor (NAVIGATION_TIMEOUT_FLOOR_MS).
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    effective = max(NAVIGATION_TIMEOUT_FLOOR_MS, timeout_ms or 0)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=effective)
    except PlaywrightTimeoutError:
        logger.warning(
            "navigation timed out; retrying once",
            extra={"url": url, "timeout_ms": effective},
        )
        page.goto(url, wait_until="domcontentloaded", timeout=effective)


def open_auth_page(pw, base_url: str, runtime, headless: bool = False) -> tuple[Any, Any, Page]:
    """Create a browser page for one-time authentication."""
    browser = launch_chromium(pw, headless=headless, slow_mo_ms=runtime.slow_mo_ms)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(runtime.timeout_ms)
    resilient_goto(page, base_url, runtime.timeout_ms)
    return browser, context, page


def open_order_page(
    playwright,
    runtime,
    state_path: Path,
    debug_browser: bool = False,
) -> tuple[Any, Any, Page]:
    """Create an automated browser page using the saved session state."""
    browser = launch_chromium(
        playwright,
        headless=False if debug_browser else runtime.headless,
        slow_mo_ms=runtime.slow_mo_ms,
    )
    context = browser.new_context(storage_state=str(state_path))
    page = context.new_page()
    page.set_default_timeout(runtime.timeout_ms)
    return browser, context, page


def close_context(context) -> None:
    """Close the Playwright browser context without surfacing cleanup errors."""
    try:
        context.close()
    except Exception:
        logger.debug("tawreed_session.close_context: best-effort context close failed")


def close_browser(browser) -> None:
    """Close the Playwright browser without surfacing cleanup errors."""
    try:
        browser.close()
    except Exception:
        logger.debug("tawreed_session.close_browser: best-effort browser close failed")


# ============================================================================
# Session validation
# ============================================================================

def _is_logged_in_marker_visible(page: Page, logged_in_marker: str, timeout_ms: int) -> bool:
    """Return whether the configured logged-in marker appears within the timeout."""
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
        logger.debug("tawreed_session._is_logged_in_marker_visible: detection failed")
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
        logger.debug("tawreed_session._ready_surface_visible: check failed")
        return False


def validate_saved_session(
    playwright,
    runtime,
    state_path,
    target_url: str,
    selectors,
    logged_in_marker: str,
    ready_selector: str,
) -> bool:
    """Open the saved session in a browser and verify the user is logged in."""
    temp_state = auth_temp_state_path(state_path)
    discard_session_state(temp_state)
    browser, context, page = open_order_page(playwright, runtime, state_path)
    try:
        resilient_goto(page, target_url, runtime.timeout_ms)
        if not _has_logged_in_marker(page, logged_in_marker, timeout_ms=5000):
            return False
        if not _ready_surface_visible(page, ready_selector):
            return False
        save_session_state(context, temp_state, is_intermediate=False)
        promote_session_state(temp_state, state_path)
        return True
    finally:
        close_context(context)
        close_browser(browser)


__all__ = [
    # State
    "auth_temp_state_path",
    "save_session_state",
    "promote_session_state",
    "discard_session_state",
    # Browser
    "open_auth_page",
    "open_order_page",
    "resilient_goto",
    "NAVIGATION_TIMEOUT_FLOOR_MS",
    "close_context",
    "close_browser",
    # Auth
    "SessionInvalidError",
    "attempt_env_login",
    "print_auth_instructions",
    "print_login_detection_result",
    "wait_for_network_idle",
    "wait_for_login_detection",
    "perform_tawreed_auth",
    # Validation
    "validate_saved_session",
]
