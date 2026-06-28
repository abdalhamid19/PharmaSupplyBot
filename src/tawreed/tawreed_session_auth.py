"""Authentication logic for Tawreed session management."""

import os
import webbrowser
from pathlib import Path

from playwright.sync_api import Page

from .tawreed_auth_waits import (
    is_logged_in_marker_visible,
    wait_for_login_detection as poll_for_login_detection,
)
from .tawreed_session_state import save_session_state


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
        save_inter=save_intermediate,
    )


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


def headless_auth_failure_message() -> str:
    """Return the user-facing failure message for hosted headless-auth attempts."""
    return (
        "Headless auth did not produce a valid Tawreed session. "
        "The site stayed on the login page or required extra human verification. "
        "Check credentials, OTP/CAPTCHA requirements, and login selectors."
    )


def open_reauth_in_browser(base_url: str, profile_key: str) -> None:
    """Open the Tawreed login page in a visible system browser for re-authentication."""
    try:
        webbrowser.open(base_url)
        print(f"[{profile_key}] Opened Tawreed login page in a visible browser window.")
    except Exception:
        print(f"[{profile_key}] Could not open a visible browser automatically.")
