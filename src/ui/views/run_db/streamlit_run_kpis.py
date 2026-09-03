"""Run header for the Run Results (database) tab."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_run_header(run: dict[str, Any]) -> None:
    """Render run identity above the KPI row."""
    st.subheader(f"{run['profile_key']} / {run['run_id']}")
    st.caption(
        f"mode={run.get('mode', '')} · command={run.get('command', '')} · "
        f"started={run.get('started_at', '')} · finished={run.get('finished_at', '-')}"
    )