"""Auto-refresh authentication when Tawreed token expires."""

from __future__ import annotations

from pathlib import Path

from .tawreed_auth_tokens import is_token_expired
from .tawreed_headless_auth_refresh import run_headless_auth_refresh


DEFAULT_AUTO_AUTH_WAIT_SECONDS = 120


def auto_refresh_auth_if_needed(
    base_url: str,
    state_path: Path,
    runtime_config,
    selectors,
    profile_key: str,
    debug: bool = False,
) -> None:
    """Refresh the saved Tawreed browser state when its access token expired."""
    if not is_token_expired(state_path):
        return

    run_headless_auth_refresh(
        base_url,
        state_path,
        runtime_config,
        selectors,
        profile_key,
        wait_seconds=DEFAULT_AUTO_AUTH_WAIT_SECONDS,
    )
    if is_token_expired(state_path):
        raise RuntimeError(_expired_after_refresh_message(profile_key))


def _expired_after_refresh_message(profile_key: str) -> str:
    """Return a clear message when login completed without a valid access token."""
    return (
        f"Auto-auth completed for profile '{profile_key}', but the Tawreed access "
        "token is still missing or expired. Check credentials and login selectors."
    )
