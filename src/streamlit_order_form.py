"""Order form helpers for the Streamlit GUI."""

from __future__ import annotations

import streamlit as st

from .streamlit_state_uploads import state_upload_fields
from .streamlit_uploads import available_excel_options


def order_form_values(app_config) -> tuple[bool, dict[str, object]]:
    """Return the submitted order form values."""
    with st.form("order_form"):
        values = order_form_fields(app_config)
        submitted = st.form_submit_button("Run Order")
    return bool(submitted), values


def order_form_fields(app_config) -> dict[str, object]:
    """Return the order form field values."""
    input_mode, excel_path_str, upload = excel_source_fields()
    profile_mode, profile_key, limit, debug_browser, highest_discount = profile_run_fields(app_config)
    uploaded_states = state_upload_fields(app_config, profile_mode, profile_key)
    return {
        "input_mode": input_mode,
        "excel_path_str": excel_path_str,
        "upload": upload,
        "profile_mode": profile_mode,
        "profile_key": profile_key,
        "limit": int(limit),
        "debug_browser": bool(debug_browser),
        "highest_discount": bool(highest_discount),
        "uploaded_states": uploaded_states,
    }


def excel_source_fields() -> tuple[str, str, object]:
    """Return the order form fields related to Excel input selection."""
    input_mode = st.radio(
        "Excel source",
        ["Existing file", "Upload file"],
        horizontal=True,
    )
    excel_path_str = existing_excel_path(input_mode, available_excel_options())
    return input_mode, excel_path_str, uploaded_excel_file(input_mode)


def profile_run_fields(app_config) -> tuple[str, str, int, bool, bool]:
    """Return the order form fields related to profile execution."""
    profile_mode = st.radio("Run target", ["Single profile", "All profiles"], horizontal=True)
    profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0)
    limit = st.number_input("Item limit", min_value=0, max_value=100000, value=50)
    highest_discount = st.checkbox("Highest discount first", value=False)
    debug_browser = st.checkbox("Debug browser", value=False)
    return str(profile_mode), str(profile_key), int(limit), bool(debug_browser), bool(highest_discount)


def existing_excel_path(input_mode: str, excel_options: list[str]) -> str:
    """Return the selected existing Excel path when that input mode is active."""
    if input_mode != "Existing file":
        return ""
    if excel_options:
        return str(st.selectbox("Excel file", excel_options, index=0))
    return str(st.text_input("Excel file path", ""))


def uploaded_excel_file(input_mode: str):
    """Return the uploaded Excel file when upload mode is active."""
    return st.file_uploader("Upload Excel", type=["xlsx"]) if input_mode == "Upload file" else None
