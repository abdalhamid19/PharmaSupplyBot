"""Browser session and authentication helpers for Tawreed Playwright flows."""

from __future__ import annotations

import os
import webbrowser
from pathlib import Path
from typing import Any

from playwright.sync_api import Page

from ..playwright_browser import launch_chromium
from .tawreed_auth_waits import (
    is_logged_in_marker_visible,
    wait_for_login_detection as poll_for_login_detection,
)


class SessionInvalidError(RuntimeError):
    """Raised when the saved login session is not valid for order placement."""


def open_auth_page(playwright, base_url: str, runtime, headless: bool = False) -> tuple[Any, Any, Page]:
    """Create a browser page for one-time authentication."""
    browser = launch_chromium(playwright, headless=headless, slow_mo_ms=runtime.slow_mo_ms)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(runtime.timeout_ms)
    page.goto(base_url, wait_until="domcontentloaded")
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


def print_auth_instructions(wait_seconds: int, headless: bool = False) -> None:
    """Explain the authentication behavior to the operator."""
    if headless:
        print(
            "Headless browser opened for credential-based login.\n"
            f"- I will wait up to {wait_seconds} seconds for Tawreed to authenticate.\n"
            "- If the site requires CAPTCHA/OTP or extra human verification, this mode will fail.\n"
        )
        return
    print(
        "Browser opened. Please complete login manually.\n"
        "- I will keep the browser open for up to "
        f"{wait_seconds} seconds waiting for login detection.\n"
        "- If the site requires OTP/CAPTCHA, finish it in the browser.\n"
    )


def wait_for_login_detection(
    page: Page,
    context,
    wait_seconds: int,
    login_email_selector: str,
    login_password_selector: str,
    logged_in_marker: str,
    state_path: Path,
    save_intermediate: bool = True,
) -> bool:
    """Poll the page until the logged-in marker appears or the timeout is reached."""
    return poll_for_login_detection(
        page,
        context,
        wait_seconds,
        login_email_selector,
        login_password_selector,
        logged_in_marker,
        state_path,
        save_session_state,
        save_intermediate=save_intermediate,
    )


def wait_for_network_idle(page: Page) -> None:
    """Wait for the page to settle without failing the flow if it times out."""
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass


def auth_temp_state_path(state_path: Path) -> Path:
    """Return the temporary path used while validating a newly captured auth session."""
    return state_path.with_name(f"{state_path.stem}.tmp{state_path.suffix}")


def print_login_detection_result(detected: bool) -> None:
    """Report whether login detection succeeded before the timeout."""
    if detected:
        print("Login detected.")
        return
    print(
        "Login marker not detected before timeout. Saving session anyway.\n"
        "If it doesn't work later, update selectors.nav.logged_in_marker in config.yaml."
    )


def headless_auth_failure_message() -> str:
    """Return the user-facing failure message for hosted headless-auth attempts."""
    return (
        "Headless auth did not produce a valid Tawreed session. "
        "The site stayed on the login page or required extra human verification. "
        "Check credentials, OTP/CAPTCHA requirements, and login selectors."
    )


def save_session_state(context, state_path: Path, is_intermediate: bool) -> None:
    """Persist the current browser storage state to disk."""
    try:
        context.storage_state(path=str(state_path))
        if is_intermediate:
            print(f"Saved intermediate session state: {state_path}")
    except Exception:
        pass


def promote_session_state(temp_state_path: Path, final_state_path: Path) -> None:
    """Replace the final saved session state with a validated temporary capture."""
    final_state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_state_path.replace(final_state_path)


def discard_session_state(state_path: Path) -> None:
    """Delete one temporary or invalid saved session state without surfacing cleanup errors."""
    try:
        state_path.unlink(missing_ok=True)
    except Exception:
        pass


def validate_saved_session(
    playwright,
    runtime,
    state_path: Path,
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
    """Verify that the saved session is still authenticated before ordering begins."""
    page.wait_for_load_state("domcontentloaded")
    if _ready_surface_visible(page, ready_selector):
        return
    if _is_login_form_visible(page, selectors):
        raise SessionInvalidError(
            "Saved session is expired or still on the login page."
        )
    short_timeout_ms = min(timeout_ms, 2000)
    if _has_logged_in_marker(page, selectors.logged_in_marker, short_timeout_ms):
        return
    if _ready_surface_visible(page, ready_selector):
        return
    if _is_login_form_visible(page, selectors):
        raise SessionInvalidError(
            "Saved session is expired or still on the login page."
        )
    raise SessionInvalidError(
        "Saved session did not expose the login page or the expected order surface."
    )


def open_reauth_in_browser(base_url: str, profile_key: str) -> None:
    """Open the Tawreed login page in a visible system browser for re-authentication."""
    try:
        webbrowser.open(base_url)
        print(f"[{profile_key}] Opened Tawreed login page in a visible browser window.")
    except Exception:
        print(f"[{profile_key}] Could not open a visible browser automatically.")


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


def _ready_surface_visible(page: Page, ready_selector: str) -> bool:
    """Return whether the requested page surface is already interactive."""
    if not ready_selector:
        return False
    try:
        page.locator(ready_selector).first.wait_for(timeout=1200)
        return True
    except Exception:
        return False
