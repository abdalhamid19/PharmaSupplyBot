"""Shared helpers and common logic for CLI command runners."""

from __future__ import annotations

from pathlib import Path

from src.core.config.config_models import AppConfig, ProfileConfig
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
    """Ensure the profile has a saved Playwright storage state file."""
    saved_state_path = state_path(profile_key)
    if saved_state_path.exists():
        return
    raise SystemExit(
        f"Missing saved session state for profile '{profile_key}'. "
        f"Run: py run.py auth --profile {profile_key}"
    )


def state_path(profile_key: str) -> Path:
    """Return the storage-state path for one profile."""
    state_dir = Path("state")
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{profile_key}.json"


def invalid_session_exit(
    base_url: str, profile_key: str, error: SessionInvalidError
) -> SystemExit:
    """Return the standard session-expired CLI exit after opening browser reauth."""
    print(f"[{profile_key}] {error}")
    print(f"Run: py run.py auth --profile {profile_key}")
    return SystemExit(
        f"Session for profile '{profile_key}' is not valid. "
        f"Run: py run.py auth --profile {profile_key}"
    )


def api_unavailable_exit(profile_key: str, error: Exception) -> SystemExit:
    """Return a clean CLI exit for strict API execution failures."""
    return SystemExit(
        f"Tawreed API unavailable for profile '{profile_key}': {error}. "
        "Use --execution-mode auto or browser, or refresh auth with: "
        f"py run.py auth --profile {profile_key}"
    )
