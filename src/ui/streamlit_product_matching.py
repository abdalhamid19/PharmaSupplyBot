"""Product matching tab for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .streamlit_product_matching_form import product_matching_form
from .streamlit_product_matching_output import (
    render_running_matching_controls,
    matching_output_csv_path,
    matching_output_log_path,
)
from .streamlit_product_matching_command import product_matching_command
from .streamlit_process import start_cli_subprocess
from .streamlit_uploads import resolve_excel_path


def render_product_matching_tab(
    app_config, default_profile: str | None, config_path: Path
) -> None:
    """Render standalone product matching controls."""
    st.subheader("Product Matching")
    if render_running_matching_controls():
        return
    submitted, values = product_matching_form(app_config, default_profile)
    if not submitted:
        return
    excel_path = resolve_excel_path(values["excel_path"], values["upload"])
    if excel_path is None:
        st.error("Please choose or upload an Excel file.")
        return
    output_path = matching_output_csv_path(str(values["profile_key"]))
    command = product_matching_command(config_path, values, excel_path, output_path)
    state = start_cli_subprocess(command, matching_output_log_path())
    state.update({"output_csv": str(output_path)})
    st.session_state["product_matching_process"] = state
    st.success("Product matching started.")
    st.rerun()


__all__ = ["render_product_matching_tab"]
