"""Product matching output handling for Streamlit."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st

from .streamlit_shared import ARTIFACTS_DIR, load_csv_rows


def render_running_matching_controls() -> bool:
    """Render a running or completed matching subprocess."""
    from .streamlit_order_process import close_order_process_output, order_process_output
    from .streamlit_process import render_command_result
    
    state = st.session_state.get("product_matching_process")
    if not state:
        return False
    returncode = state["process"].poll()
    output_text = order_process_output(Path(state["output_path"]))
    if returncode is None:
        st.warning("Product matching is running.")
        if st.button("Refresh Matching Status"):
            st.rerun()
        if output_text:
            st.code(output_text[-4000:], language="text")
        render_matching_output_table(Path(state["output_csv"]))
        return True
    close_order_process_output(state)
    render_command_result(_matching_process_result(state, returncode, output_text))
    render_matching_output_table(Path(state["output_csv"]))
    st.session_state.pop("product_matching_process", None)
    return False


def render_matching_output_table(output_path: Path) -> None:
    """Render the latest product matching CSV output."""
    rows = load_csv_rows(output_path)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def matching_output_csv_path(profile_key: str) -> Path:
    """Return a unique CSV path for a Streamlit matching run."""
    return ARTIFACTS_DIR / profile_key / f"product_matching_{int(time.time())}.csv"


def matching_output_log_path() -> Path:
    """Return a unique output log path for a Streamlit matching run."""
    from .streamlit_order import run_control_dir
    return run_control_dir() / f"product_matching_output_{int(time.time())}.log"


def _matching_process_result(state: dict, returncode: int, output_text: str) -> dict:
    return {
        "ok": returncode == 0,
        "exit_code": returncode,
        "command": " ".join(state["command"]),
        "output": output_text,
        "error_type": "ProcessError" if returncode else "",
        "error_message": f"Exited with status code {returncode}." if returncode else "",
    }


__all__ = [
    "render_running_matching_controls",
    "render_matching_output_table",
    "matching_output_csv_path",
    "matching_output_log_path",
    "_matching_process_result",
]
