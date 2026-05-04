"""Session-state helpers for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

from .streamlit_default_state import default_state_bytes


STATE_DIR = Path("state")


def state_file_path(profile_key: str) -> Path:
    """Return the saved session-state path for one profile."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{profile_key}.json"


def state_file_exists(profile_key: str) -> bool:
    """Return whether a saved session-state file exists for one profile."""
    return state_file_path(profile_key).exists()


def ensure_default_state_files(profile_keys: list[str]) -> None:
    """Materialize any configured default state files for the requested profiles."""
    for profile_key in profile_keys:
        ensure_default_state_file(profile_key)


def ensure_default_state_file(profile_key: str) -> Path | None:
    """Persist one configured default state file when the live state file is missing."""
    path = state_file_path(profile_key)
    if path.exists():
        return path
    default_bytes = default_state_bytes(profile_key)
    if default_bytes is None:
        return None
    path.write_bytes(default_bytes)
    return path


def persist_uploaded_states(uploaded_states: dict[str, object]) -> None:
    """Persist all uploaded session-state files that were provided."""
    for profile_key, uploaded_file in uploaded_states.items():
        if uploaded_file is None:
            continue
        persist_uploaded_state(profile_key, uploaded_file)


def persist_uploaded_state(profile_key: str, uploaded_file) -> Path:
    """Persist one uploaded session-state file for one profile."""
    path = state_file_path(profile_key)
    path.write_bytes(uploaded_file.getvalue())
    return path


def missing_state_profiles(profile_keys: list[str]) -> list[str]:
    """Return the target profiles that still lack a saved session-state file."""
    return [profile_key for profile_key in profile_keys if not state_file_exists(profile_key)]
