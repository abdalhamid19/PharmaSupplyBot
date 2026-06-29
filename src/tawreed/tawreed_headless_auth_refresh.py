"""Headless Tawreed login refresh for expired saved sessions."""

from __future__ import annotations
import os
from pathlib import Path
from .tawreed_constants import PRODUCTS_PAGE_ROUTE
from .tawreed_session import (
    attempt_env_login, auth_temp_state_path, close_browser, close_context,
    discard_session_state, headless_auth_failure_message, open_auth_page,
    print_auth_instructions, print_login_detection_result, promote_session_state,
    save_session_state, validate_saved_session, wait_for_login_detection, wait_for_network_idle
)


def run_headless_auth_refresh(
    base_url, state_path, runtime_config, selectors,
    profile_key, wait_seconds, headless=True
):
    """Re-authenticate headlessly and atomically replace the saved state file."""
    from playwright.sync_api import sync_playwright

    require_env_credentials(profile_key)
    with sync_playwright() as playwright:
        _run_auth_refresh_session(
            playwright, base_url, runtime_config, selectors, 
            state_path, profile_key, wait_seconds, headless
        )


def _run_auth_refresh_session(
    playwright, base_url, runtime_config, selectors, 
    state_path, profile_key, wait_seconds, headless
):
    temp_state_path = auth_temp_state_path(state_path)
    discard_session_state(temp_state_path)
    browser, context, page = open_auth_page(
        playwright, base_url, runtime_config, headless=headless
    )
    try:
        _capture_and_validate_session(
            playwright, runtime_config, page, context, selectors, 
            temp_state_path, base_url, wait_seconds
        )
        promote_session_state(temp_state_path, state_path)
        msg = f"[{profile_key}] Auto-refreshed Tawreed session state: {state_path}"
        print(msg)
    except Exception:
        discard_session_state(temp_state_path)
        raise
    finally:
        close_context(context)
        close_browser(browser)


def _capture_and_validate_session(
    playwright, runtime_config, page, context, selectors, 
    temp_state_path, base_url, wait_seconds
):
    capture_headless_state(
        page, context, selectors, temp_state_path, wait_seconds
    )
    validate_saved_session(
        playwright, runtime_config, temp_state_path, 
        products_page_url(base_url), selectors, 
        selectors.item_search_input
    )


def capture_headless_state(
    page, context, selectors, state_path: Path, wait_seconds: int
):
    attempt_env_login(page, selectors)
    print_auth_instructions(wait_seconds, headless=True)
    detected = wait_for_login_detection(
        page, context, wait_seconds, selectors.login_email, 
        selectors.login_password, selectors.logged_in_marker, 
        state_path, save_intermediate=False
    )
    wait_for_network_idle(page)
    print_login_detection_result(detected)
    save_session_state(context, state_path, is_intermediate=False)
    if not detected:
        raise RuntimeError(headless_auth_failure_message())


def require_env_credentials(profile_key: str) -> None:
    email = os.getenv("TAWREED_EMAIL", "").strip()
    password = os.getenv("TAWREED_PASSWORD", "").strip()
    if email and password:
        return
    raise RuntimeError(
        f"Token expired for profile '{profile_key}', but automatic login credentials "
        "are not configured. Set TAWREED_EMAIL and TAWREED_PASSWORD or run "
        f"auth manually: py run.py auth --profile {profile_key}"
    )


def products_page_url(base_url: str) -> str:
    if "#/" in base_url:
        origin, _ = base_url.split("#/", 1)
        return f"{origin}{PRODUCTS_PAGE_ROUTE}"
    return base_url
