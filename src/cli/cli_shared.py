"""Shared helpers and common logic for CLI command runners."""

from __future__ import annotations

import logging
from pathlib import Path

from src.core.config.config_models import AppConfig, ProfileConfig
from src.core.errors import APIUnavailableError, AuthError
from src.tawreed.tawreed import TawreedBot
from src.tawreed.auth.tawreed_session import SessionInvalidError


def build_bot(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    debug_browser: bool = False,
    **options,
) -> TawreedBot:
    """Create a Tawreed bot instance for one profile."""
    return TawreedBot(
        app_config,
        profile_key,
        profile,
        state_path(profile_key),
        debug_browser=debug_browser,
        **options,
    )


def require_state_file(profile_key: str) -> None:
    """Ensure the profile has a saved Playwright storage state file.

    Raises :class:`AuthError` (exit code 3) when the state is missing so
    the runner can map it to a clean CLI failure instead of a stack trace.
    """
    saved_state_path = state_path(profile_key)
    if saved_state_path.exists():
        return
    raise AuthError(
        f"Missing saved session state for profile '{profile_key}'.",
        profile=profile_key,
        hint=f"Run: py run.py auth --profile {profile_key}",
    )


def state_path(profile_key: str) -> Path:
    """Return the storage-state path for one profile."""
    state_dir = Path("state")
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{profile_key}.json"


def raise_invalid_session(
    profile_key: str, error: SessionInvalidError
) -> None:
    """Raise the standard session-expired error after opening browser reauth.

    Replaces the legacy ``invalid_session_exit`` helper. The previous
    implementation returned a ``SystemExit`` instance (which only works
    when the caller is itself about to ``raise`` it). Raising directly
    is safer, more consistent, and gives us a typed ``AuthError`` to
    log with ``logger.exception``.
    """
    raise AuthError(
        f"Session for profile '{profile_key}' is not valid: {error}",
        profile=profile_key,
        hint=f"Run: py run.py auth --profile {profile_key}",
    )


def raise_api_unavailable(profile_key: str, error: Exception) -> None:
    """Raise the standard API-unavailable error for strict execution modes.

    Replaces the legacy ``api_unavailable_exit`` helper. The CLI runner
    converts :class:`APIUnavailableError` into exit code 4.
    """
    raise APIUnavailableError(
        f"Tawreed API unavailable for profile '{profile_key}': {error}. "
        "Use --execution-mode auto or browser, or refresh auth with: "
        f"py run.py auth --profile {profile_key}",
        profile=profile_key,
    )


__all__ = [
    "build_bot",
    "require_state_file",
    "state_path",
    "raise_invalid_session",
    "raise_api_unavailable",
]