"""State file preparation for Streamlit order tab."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .streamlit_state import ensure_default_state_files, missing_state_profiles
from .streamlit_order_paths import _latest_order_summary_path


def prepare_order_state_files(app_config, form_values: dict[str, object]) -> bool:
    """Ensure every target profile has a ready session-state file."""
    target_profiles = target_profile_keys(app_config, form_values)
    ensure_default_state_files(target_profiles)
    missing_profiles = missing_state_profiles(target_profiles)
    if not missing_profiles:
        return True
    missing_text = ", ".join(f"`{profile_key}`" for profile_key in missing_profiles)
    st.error(f"Missing session-state JSON for: {missing_text}")
    st.info(
        "Upload `state/<profile>.json` from a machine where you already ran `py run.py auth`."
    )
    return False


def target_profile_keys(app_config, form_values: dict[str, object]) -> list[str]:
    """Return the profiles targeted by one order submission."""
    if form_values["profile_mode"] == "Single profile":
        return [str(form_values["profile_key"])]
    return list(app_config.profiles.keys())


def _profile_key_for_state(form_values: dict[str, object]) -> str:
    """Return the single profile key used for result watching."""
    return str(form_values.get("profile_key") or "wardany")


def _completed_summary_path(state: dict[str, object]) -> Path:
    """Return the completed run summary path for process rendering."""
    latest = _latest_order_summary_path(
        str(state.get("profile_key", "wardany")), bool(state.get("match_only"))
    )
    return latest or Path(str(state["summary_path"]))


def _completed_previous_count(state: dict[str, object]) -> int:
    """Return previous row count only when the watched path did not change."""
    completed = _completed_summary_path(state)
    if completed == Path(str(state["summary_path"])):
        return int(state["previous_row_count"])
    return 0
