"""Authentication tab rendering for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .streamlit_process import render_command_result, run_cli_subprocess


def render_auth_tab(app_config, default_profile: str | None, config_path: Path) -> None:
    """Render the auth workflow controls."""
    st.subheader("Interactive Login")
    if not default_profile:
        st.warning("No profiles found in config.")
        return
    submitted, profile_key, wait_seconds = auth_form_values(app_config)
    render_local_auth_guidance(profile_key)
    if not submitted:
        return
    with st.spinner("Opening browser for login..."):
        result = run_cli_subprocess(auth_command(profile_key, wait_seconds, config_path))
    render_command_result(result)


def auth_form_values(app_config) -> tuple[bool, str, int]:
    """Return the submitted auth form values."""
    with st.form("auth_form"):
        profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0)
        wait_seconds = st.number_input("Wait seconds", min_value=60, max_value=3600, value=600)
        submitted = st.form_submit_button("Start Auth Browser")
    return bool(submitted), str(profile_key), int(wait_seconds)


def render_local_auth_guidance(profile_key: str) -> None:
    """Render the local-auth fallback instructions for one selected profile."""
    st.info("If the hosted browser flow is unavailable, authenticate once on your local machine.")
    st.code(local_auth_command(profile_key), language="powershell")
    st.caption(f"Then upload `state/{profile_key}.json` in the `Order` tab.")


def local_auth_command(profile_key: str) -> str:
    """Return the local CLI auth command for one profile."""
    return f"py run.py auth --profile {profile_key}"


def auth_command(profile_key: str, wait_seconds: int, config_path: Path) -> list[str]:
    """Return the CLI command arguments for one auth run."""
    return [
        "auth",
        "--config",
        str(config_path),
        "--profile",
        profile_key,
        "--wait-seconds",
        str(wait_seconds),
    ]
