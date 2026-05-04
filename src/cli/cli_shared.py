"""Shared helpers and common logic for CLI command runners."""

from __future__ import annotations

from pathlib import Path

from ..core.config.config_models import AppConfig, ProfileConfig
from ..tawreed.tawreed import TawreedBot
from ..tawreed.tawreed_session import SessionInvalidError, open_reauth_in_browser


def build_bot(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    debug_browser: bool = False,
    stop_flag_path: Path | None = None,
) -> TawreedBot:
    """Create a Tawreed bot instance for one profile."""
    return TawreedBot(
        config=app_config,
        profile_key=profile_key,
        profile=profile,
        state_path=state_path(profile_key),
        debug_browser=debug_browser,
        stop_flag_path=stop_flag_path,
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


def invalid_session_exit(base_url: str, profile_key: str, error: SessionInvalidError) -> SystemExit:
    """Return the standard session-expired CLI exit after opening browser reauth."""
    print(f"[{profile_key}] {error}")
    open_reauth_in_browser(base_url, profile_key)
    return SystemExit(
        f"Session for profile '{profile_key}' is not valid. "
        f"Run: py run.py auth --profile {profile_key}"
    )
