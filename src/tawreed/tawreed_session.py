"""Browser session and authentication helpers for Tawreed Playwright flows."""

from __future__ import annotations

from playwright.sync_api import Page

from .tawreed_session_browser import (
    open_auth_page, open_order_page, close_context, close_browser
)
from .tawreed_session_auth import (
    SessionInvalidError,
    attempt_env_login,
    print_auth_instructions,
    wait_for_login_detection,
    wait_for_network_idle,
    print_login_detection_result,
    headless_auth_failure_message,
    open_reauth_in_browser,
)
from .tawreed_session_state import (
    auth_temp_state_path,
    save_session_state,
    promote_session_state,
    discard_session_state,
)
from .tawreed_session_validation import (
    validate_saved_session, ensure_logged_in,
    _is_logged_in_marker_visible, _has_logged_in_marker,
    _is_login_form_visible, _ready_surface_visible
)


def perform_tawreed_auth(bot, wait_seconds: int, headless: bool) -> None:
    """Authenticate in either interactive or headless mode and save session state."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        temp_state_path = auth_temp_state_path(bot.state_path)
        discard_session_state(temp_state_path)
        browser, context, page = open_auth_page(
            p, bot.config.base_url, bot.config.runtime, headless=headless
        )
        try:
            attempt_env_login(page, bot.selectors)
            print_auth_instructions(wait_seconds, headless=headless)
            _poll_and_save_auth(bot, page, context, wait_seconds, temp_state_path, headless)
            _finalize_tawreed_auth(bot, p, temp_state_path)
        except Exception as error:
            _handle_auth_failure(bot, page, error, temp_state_path, headless)
            raise
        finally:
            close_context(context)
            close_browser(browser)


def _poll_and_save_auth(bot, page, context, wait_seconds, temp_state_path, headless):
    """Wait for login markers and persist the captured session state."""
    detected = wait_for_login_detection(
        page, context, wait_seconds,
        bot.selectors.login_email, bot.selectors.login_password,
        bot.selectors.logged_in_marker, temp_state_path,
        save_intermediate=not headless,
    )
    wait_for_network_idle(page)
    print_login_detection_result(detected)
    save_session_state(context, temp_state_path, is_intermediate=False)
    if headless and not detected:
        raise bot._headless_auth_error()


def _finalize_tawreed_auth(bot, p, temp_state_path):
    """Validate the newly captured session and promote it to the final state path."""
    validate_saved_session(
        p, bot.config.runtime, temp_state_path,
        bot._products_page_url(), bot.selectors, bot.selectors.item_search_input
    )
    promote_session_state(temp_state_path, bot.state_path)
    print(f"Saved validated session state: {bot.state_path}")


def _handle_auth_failure(bot, page, error, temp_state_path, headless):
    """Clean up and record diagnostics after a failed authentication attempt."""
    from .tawreed_artifacts import dump_artifacts
    if headless:
        dump_artifacts(
            page, bot.profile_key, label="headless_auth_error",
            details=f"headless_auth_error: {error}",
        )
    discard_session_state(temp_state_path)


__all__ = [
    "SessionInvalidError",
    "open_auth_page",
    "open_order_page",
    "attempt_env_login",
    "print_auth_instructions",
    "wait_for_login_detection",
    "wait_for_network_idle",
    "auth_temp_state_path",
    "print_login_detection_result",
    "headless_auth_failure_message",
    "save_session_state",
    "promote_session_state",
    "discard_session_state",
    "validate_saved_session",
    "ensure_logged_in",
    "open_reauth_in_browser",
    "perform_tawreed_auth",
    "close_context",
    "close_browser",
    "_is_logged_in_marker_visible",
    "_has_logged_in_marker",
    "_is_login_form_visible",
    "_ready_surface_visible",
]
