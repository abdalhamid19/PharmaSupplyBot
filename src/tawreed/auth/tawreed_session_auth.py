"""Authentication logic for Tawreed session management."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page


logger = logging.getLogger(__name__)


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
    """Log authentication behaviour guidance to the operator.

    The message still uses multi-line formatting because it's explaining
    the flow rather than reporting a single event.
    """
    if headless:
        logger.warning(
            "headless login flow instructions",
            extra={
                "wait_seconds": wait_seconds,
                "instructions": (
                    "Headless browser opened for credential-based login. "
                    f"I will wait up to {wait_seconds} seconds for Tawreed to "
                    "authenticate. If the site requires CAPTCHA/OTP or extra "
                    "human verification, this mode will fail."
                ),
            },
        )
        return
    logger.warning(
        "interactive login flow instructions",
        extra={
            "wait_seconds": wait_seconds,
            "instructions": (
                "Browser opened. Please complete login manually. "
                f"I will keep the browser open for up to {wait_seconds} seconds "
                "waiting for login detection. If the site requires OTP/CAPTCHA, "
                "finish it in the browser."
            ),
        },
    )


def print_login_detection_result(detected: bool) -> None:
    """Log the result of login detection."""
    if detected:
        logger.info("login detected")
    else:
        logger.warning("login not detected within timeout")


def wait_for_network_idle(page) -> None:
    """Wait for network activity to settle after login."""
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass


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
    )


__all__ = [
    "SessionInvalidError",
    "attempt_env_login",
    "print_auth_instructions",
    "print_login_detection_result",
    "wait_for_network_idle",
    "perform_tawreed_auth",
]
