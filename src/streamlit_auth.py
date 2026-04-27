"""Authentication tab rendering for the Streamlit GUI."""

from __future__ import annotations

import streamlit as st

from .streamlit_process import render_command_result, run_cli_subprocess
from .streamlit_shared import sidebar_config_path


def render_auth_tab(app_config, default_profile: str | None) -> None:
    """Render the auth workflow controls."""
    st.subheader("Interactive Login")
    if not default_profile:
        st.warning("No profiles found in config.")
        return
    submitted, profile_key, wait_seconds = auth_form_values(app_config)
    if not submitted:
        return
    with st.spinner("Opening browser for login..."):
        result = run_cli_subprocess(auth_command(profile_key, wait_seconds))
    render_command_result(result)


def auth_form_values(app_config) -> tuple[bool, str, int]:
    """Return the submitted auth form values."""
    with st.form("auth_form"):
        profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0)
        wait_seconds = st.number_input("Wait seconds", min_value=60, max_value=3600, value=600)
        submitted = st.form_submit_button("Start Auth Browser")
    return bool(submitted), str(profile_key), int(wait_seconds)


def auth_command(profile_key: str, wait_seconds: int) -> list[str]:
    """Return the CLI command arguments for one auth run."""
    return [
        "auth",
        "--config",
        str(sidebar_config_path()),
        "--profile",
        profile_key,
        "--wait-seconds",
        str(wait_seconds),
    ]
