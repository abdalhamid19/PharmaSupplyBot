"""Results tab composition for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .streamlit_results_selection import (
    command_options,
    command_profile_options,
    command_run_options,
)
from .streamlit_results_management import (
    clear_profile_result_data,
    safe_profile_artifact_paths,
    summary_sources,
)
from .streamlit_results_rendering import (
    render_command_run_results,
    render_run_dir_results,
    run_summary_rows,
    preferred_run_summary_path,
    render_selected_profile_results,
    render_clear_profile_results_controls,
    render_profile_summaries,
    render_fresh_run_analysis,
)
from .streamlit_results_tables import (
    render_run_table,
    render_order_ai_trace_summary,
    render_recent_run_files,
    render_recent_artifact_files,
)
from .streamlit_shared import ARTIFACTS_DIR


def render_results_tab(default_profile: str | None) -> None:
    """Render summary/result browsing tools."""
    st.subheader("Results")
    if not default_profile:
        st.warning("No profiles found in config.")
        return
    if render_command_run_results():
        return
    profile_key = st.selectbox("Artifacts profile", command_options(), index=0)
    render_selected_profile_results(profile_key)


__all__ = [
    "render_results_tab",
    "render_command_run_results",
    "command_options",
    "command_profile_options",
    "command_run_options",
    "render_run_dir_results",
    "run_summary_rows",
    "preferred_run_summary_path",
    "render_selected_profile_results",
    "render_clear_profile_results_controls",
    "clear_profile_result_data",
    "safe_profile_artifact_paths",
    "summary_sources",
    "render_profile_summaries",
    "render_fresh_run_analysis",
]
