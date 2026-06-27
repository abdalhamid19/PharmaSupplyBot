"""Tawreed authentication flow management."""

from __future__ import annotations

from pathlib import Path

from .tawreed_session import (
    headless_auth_failure_message,
    perform_tawreed_auth,
)


class TawreedAuthFlow:
    """Handles Tawreed authentication operations."""

    def __init__(self, bot):
        """Initialize auth flow with bot instance."""
        self.bot = bot

    def auth_interactive(self, wait_seconds: int = 600) -> None:
        """Open a visible browser and persist session state after manual login."""
        self._auth(wait_seconds=wait_seconds, headless=False)

    def auth_headless(self, wait_seconds: int = 120) -> None:
        """Run a headless login attempt and persist session state when credentials succeed."""
        self._auth(wait_seconds=wait_seconds, headless=True)

    def _auth(self, wait_seconds: int, headless: bool) -> None:
        """Authenticate in either interactive or headless mode and save session state."""
        perform_tawreed_auth(self.bot, wait_seconds, headless)

    def _headless_auth_error(self) -> Exception:
        """Return the explicit auth failure used when hosted login never leaves the login page."""
        return RuntimeError(headless_auth_failure_message())

    def ensure_valid_auth(self) -> None:
        """Verify token is valid or refresh authentication automatically."""
        from .tawreed_auto_auth import auto_refresh_auth_if_needed

        auto_refresh_auth_if_needed(
            self.bot.config.base_url,
            self.bot.state_path,
            self.bot.config.runtime,
            self.bot.selectors,
            self.bot.profile_key,
            auth_lock=self.bot.auth_lock,
            worker_id=self.bot.worker_id,
        )
