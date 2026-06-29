"""Session management for Tawreed authentication - unified module."""

from __future__ import annotations

import os
import webbrowser
from pathlib import Path
from typing import Any

from playwright.sync_api import Page

from .tawreed_login_detection import (
    is_logged_in_marker_visible,
    login_detected,
)
from .tawreed_playwright_browser import launch_chromium
from .tawreed_auth import headless_auth_failure_message, wait_for_login_detection


# ============================================================================
# Session state management (from tawreed_session_state.py)
# ============================================================================

def auth_temp_state_path(state_path: Path) -> Path:
    """Return the temporary path used while validating a newly captured auth session."""
    return state_path.with_name(f"{state_path.stem}.tmp{state_path.suffix}")


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


# ============================================================================
# Browser operations (from tawreed_session_browser.py)
# ============================================================================

def open_auth_page(pw, base_url: str, runtime, headless: bool = False) -> tuple[Any, Any, Page]:
    """Create a browser page for one-time authentication."""
    browser = launch_chromium(pw, headless=headless, slow_mo_ms=runtime.slow_mo_ms)
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


# ============================================================================
# Authentication logic (from tawreed_session_auth.py)
# ============================================================================

class SessionInvalidError(RuntimeError):
    """Raised when the saved login session is not valid for order placement."""


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
    except Exception as error:
        raise RuntimeError(
            "Could not submit Tawreed login credentials. "
            "Check selectors.login.email_input, password_input, and submit_button."
        ) from error


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


def print_login_detection_result(detected: bool) -> None:
    """Print the result of login detection."""
    if detected:
        print("Login detected.")
    else:
        print("Login not detected within timeout.")


def wait_for_network_idle(page) -> None:
    """Wait for network activity to settle after login."""
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass


def wait_for_login_detection(
    page: Page,
    context,
    wait_seconds: int,
    login_email_selector: str,
    login_password_selector: str,
    logged_in_marker: str,
    state_path: Path,
    save_session_state,
    save_intermediate: bool = True,
) -> bool:
    """Poll the page until the logged-in marker appears or timeout is reached."""
    from .tawreed_auth import _initial_wait_state, _advance_wait_state, _wait_budget_ms, _save_state_if_due
    
    ws = _initial_wait_state(wait_seconds)
    while ws["total_waited_ms"] < ws["wait_budget_ms"]:
        if login_detected(page, ws["poll_ms"], email_sel=login_email_selector, pwd_sel=login_password_selector, marker=logged_in_marker):
            return True
        _advance_wait_state(ws, context, state_path, save_session_state, save_intermediate)
    return False


def perform_tawreed_auth(bot, wait_seconds: int, headless: bool) -> None:
    """Perform the complete Tawreed authentication flow."""
    from .tawreed_headless_auth_refresh import run_headless_auth_refresh
    
    print_auth_instructions(wait_seconds, headless)
    run_headless_auth_refresh(
        bot.config.base_url,
        bot.state_path,
        bot.config.runtime,
        bot.selectors,
        bot.profile_key,
        wait_seconds=wait_seconds,
        headless=headless,
    )


# ============================================================================
# Session validation (from tawreed_session_validation.py)
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
    logged_in_marker: str,
    ready_selector: str,
) -> bool:
    """Open the saved session in a browser and verify the user is logged in."""
    temp_state = auth_temp_state_path(state_path)
    discard_session_state(temp_state)
    browser, context, page = open_order_page(playwright, runtime, state_path)
    try:
        page.goto(target_url, wait_until="domcontentloaded")
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
