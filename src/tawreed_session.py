"""Browser session and authentication helpers for Tawreed Playwright flows."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from playwright.sync_api import Page


def open_auth_page(playwright, base_url: str, runtime) -> tuple[Any, Any, Page]:
    """Create a visible browser page for one-time manual authentication."""
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=runtime.slow_mo_ms,
    )
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(runtime.timeout_ms)
    page.goto(base_url, wait_until="domcontentloaded")
    return browser, context, page


def open_order_page(playwright, runtime, state_path: Path) -> tuple[Any, Any, Page]:
    """Create an automated browser page using the saved session state."""
    browser = playwright.chromium.launch(
        headless=runtime.headless,
        slow_mo=runtime.slow_mo_ms,
    )
    context = browser.new_context(storage_state=str(state_path))
    page = context.new_page()
    page.set_default_timeout(runtime.timeout_ms)
    return browser, context, page


def attempt_env_login(page: Page, selectors) -> None:
    """Try to prefill and submit login credentials from environment variables."""
    email = os.getenv("TAWREED_EMAIL", "").strip()
    password = os.getenv("TAWREED_PASSWORD", "").strip()
    if not email or not password:
        return
    try:
        page.locator(selectors.login_email).first.fill(email)
        page.locator(selectors.login_password).first.fill(password)
        page.locator(selectors.login_submit).first.click()
    except Exception:
        pass


def print_auth_instructions(wait_seconds: int) -> None:
    """Explain the manual login window behavior to the operator."""
    print(
        "Browser opened. Please complete login manually.\n"
        f"- I will keep the browser open for up to {wait_seconds} seconds waiting for login detection.\n"
        "- If the site requires OTP/CAPTCHA, finish it in the browser.\n"
    )


def wait_for_login_detection(page: Page, context, wait_seconds: int, logged_in_marker: str, state_path: Path) -> bool:
    """Poll the page until the logged-in marker appears or the timeout is reached."""
    poll_ms = 2000
    save_every_ms = 5000
    total_waited_ms = 0
    since_last_save_ms = 0
    while total_waited_ms < _wait_budget_ms(wait_seconds):
        if _is_logged_in_marker_visible(page, logged_in_marker, poll_ms):
            return True
        total_waited_ms += poll_ms
        since_last_save_ms += poll_ms
        since_last_save_ms = _save_state_if_due(
            context,
            state_path,
            since_last_save_ms,
            save_every_ms,
        )
    return False


def wait_for_network_idle(page: Page) -> None:
    """Wait for the page to settle without failing the flow if it times out."""
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass


def print_login_detection_result(detected: bool) -> None:
    """Report whether login detection succeeded before the timeout."""
    if detected:
        print("Login detected.")
        return
    print(
        "Login marker not detected before timeout. Saving session anyway.\n"
        "If it doesn't work later, update selectors.nav.logged_in_marker in config.yaml."
    )


def save_session_state(context, state_path: Path, is_intermediate: bool) -> None:
    """Persist the current browser storage state to disk."""
    try:
        context.storage_state(path=str(state_path))
        if is_intermediate:
            print(f"Saved intermediate session state: {state_path}")
    except Exception:
        pass


def ensure_logged_in(page: Page, selectors, timeout_ms: int, ready_selector: str = "") -> None:
    """Verify that the saved session is still authenticated before ordering begins."""
    page.wait_for_load_state("domcontentloaded")
    if _ready_surface_visible(page, ready_selector):
        return
    if _is_login_form_visible(page, selectors):
        return
    short_timeout_ms = min(timeout_ms, 2000)
    if _has_logged_in_marker(page, selectors.logged_in_marker, short_timeout_ms):
        return
    if _ready_surface_visible(page, ready_selector):
        return
    if _is_login_form_visible(page, selectors):
        return


def close_context(context) -> None:
    """Close the Playwright browser context without surfacing cleanup errors."""
    try:
        context.close()
    except Exception:
        pass


def close_browser(browser) -> None:
    """Close the Playwright browser without surfacing cleanup errors."""
    try:
        browser.close()
    except Exception:
        pass


def _is_logged_in_marker_visible(page: Page, logged_in_marker: str, timeout_ms: int) -> bool:
    """Return whether the configured logged-in marker appears within the timeout."""
    try:
        page.locator(logged_in_marker).first.wait_for(timeout=timeout_ms)
        return True
    except Exception:
        return False


def _has_logged_in_marker(page: Page, logged_in_marker: str, timeout_ms: int) -> bool:
    """Return whether the configured logged-in marker is visible."""
    return _is_logged_in_marker_visible(page, logged_in_marker, timeout_ms)


def _wait_budget_ms(wait_seconds: int) -> int:
    """Return the total wait budget in milliseconds."""
    return max(1, int(wait_seconds)) * 1000


def _save_state_if_due(
    context,
    state_path: Path,
    since_last_save_ms: int,
    save_every_ms: int,
) -> int:
    """Persist intermediate session state when the save interval has elapsed."""
    if since_last_save_ms < save_every_ms:
        return since_last_save_ms
    save_session_state(context, state_path, is_intermediate=True)
    return 0


def _is_login_form_visible(page: Page, selectors) -> bool:
    """Return whether the login form is still visible on the current page."""
    try:
        login_email_visible = page.locator(selectors.login_email).first.is_visible(timeout=2000)
        login_password_visible = page.locator(selectors.login_password).first.is_visible(timeout=2000)
        if login_email_visible or login_password_visible:
            raise RuntimeError("Still on login page (login inputs visible).")
        return False
    except Exception:
        return True


def _ready_surface_visible(page: Page, ready_selector: str) -> bool:
    """Return whether the requested page surface is already interactive."""
    if not ready_selector:
        return False
    try:
        page.locator(ready_selector).first.wait_for(timeout=1200)
        return True
    except Exception:
        return False
