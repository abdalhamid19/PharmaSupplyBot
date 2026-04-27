"""State-upload widgets for the Streamlit order form."""

from __future__ import annotations

import streamlit as st

from .streamlit_state import state_file_exists


def state_upload_fields(app_config, profile_mode: str, profile_key: str) -> dict[str, object]:
    """Return any uploaded session-state files for the target profiles."""
    st.caption(
        "Upload `state/<profile>.json` for each target profile when running online. "
        "If nothing is uploaded, the app uses any configured default state on the server."
    )
    if profile_mode == "Single profile":
        return single_profile_state_upload(profile_key)
    return all_profile_state_uploads(app_config)


def single_profile_state_upload(profile_key: str) -> dict[str, object]:
    """Return one uploaded session-state file mapping for a single profile run."""
    show_state_status(profile_key)
    uploaded_file = st.file_uploader(
        f"Session state JSON for {profile_key}",
        type=["json"],
        key=f"state_upload_{profile_key}",
    )
    return {profile_key: uploaded_file}


def all_profile_state_uploads(app_config) -> dict[str, object]:
    """Return uploaded session-state mappings for an all-profiles run."""
    uploaded_states: dict[str, object] = {}
    for profile_key in app_config.profiles.keys():
        show_state_status(profile_key)
        uploaded_states[profile_key] = st.file_uploader(
            f"Session state JSON for {profile_key}",
            type=["json"],
            key=f"state_upload_{profile_key}",
        )
    return uploaded_states


def show_state_status(profile_key: str) -> None:
    """Render whether a saved session-state file already exists for one profile."""
    state_status = "found" if state_file_exists(profile_key) else "missing"
    st.caption(f"Current saved state for `{profile_key}`: {state_status}")
