"""Hosted headless-auth helpers for the Streamlit GUI."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from .streamlit_process import render_command_result, run_cli_subprocess


def render_headless_auth(app_config, config_path: Path) -> None:
    """Render hosted headless-auth controls and execute them when submitted."""
    st.subheader("Cloud Auth")
    submitted, profile_key, wait_seconds, email, password = headless_auth_form_values(app_config)
    if not submitted:
        return
    if not email or not password:
        st.error("Email and password are required for headless auth.")
        return
    with st.spinner("Running headless Tawreed login..."):
        result = run_cli_subprocess(
            headless_auth_command(profile_key, wait_seconds, config_path),
            env_overrides=auth_env_overrides(email, password),
        )
    render_command_result(result)


def headless_auth_form_values(app_config) -> tuple[bool, str, int, str, str]:
    """Return the submitted hosted-auth form values."""
    with st.form("headless_auth_form"):
        profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0, key="cloud_auth")
        wait_seconds = st.number_input("Wait seconds", min_value=15, max_value=300, value=90)
        email = st.text_input("Tawreed email", value=default_auth_email())
        password = st.text_input("Tawreed password", value=default_auth_password(), type="password")
        submitted = st.form_submit_button("Run Cloud Auth")
    return bool(submitted), str(profile_key), int(wait_seconds), str(email).strip(), str(password)


def headless_auth_command(profile_key: str, wait_seconds: int, config_path: Path) -> list[str]:
    """Return the CLI command arguments for one headless auth run."""
    return [
        "auth",
        "--config",
        str(config_path),
        "--profile",
        profile_key,
        "--headless",
        "--wait-seconds",
        str(wait_seconds),
    ]


def auth_env_overrides(email: str, password: str) -> dict[str, str]:
    """Return environment overrides used for hosted headless auth."""
    return {
        "TAWREED_EMAIL": email,
        "TAWREED_PASSWORD": password,
    }


def default_auth_email() -> str:
    """Return the default Tawreed email from env or Streamlit secrets."""
    return os.getenv("TAWREED_EMAIL", "").strip() or secret_string("tawreed_email")


def default_auth_password() -> str:
    """Return the default Tawreed password from env or Streamlit secrets."""
    return os.getenv("TAWREED_PASSWORD", "").strip() or secret_string("tawreed_password")


def secret_string(key: str) -> str:
    """Return one Streamlit secret as a string or an empty fallback."""
    try:
        return str(st.secrets.get(key, "")).strip()
    except Exception:  # noqa: BLE001
        return ""
