"""Background order process controls for Streamlit order tab."""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from .streamlit_results import render_fresh_run_analysis
from .streamlit_process import render_command_result, start_cli_subprocess
from .streamlit_shared import csv_row_count, load_new_summary_rows
from .streamlit_order_paths import order_output_path, order_stop_flag_path
from .streamlit_order_state import _completed_summary_path, _completed_previous_count


def render_running_order_controls() -> bool:
    """Render controls for a background order process when one is active."""
    state = st.session_state.get("order_process")
    if not state:
        return False
    process = state["process"]
    returncode = process.poll()
    output_text = order_process_output(Path(state["output_path"]))
    if returncode is None:
        st.warning("Order flow is running.")
        col_stop, col_refresh = st.columns(2)
        with col_stop:
            if st.button("Stop Order", type="primary"):
                Path(state["stop_flag_path"]).write_text(
                    "stop requested\n", encoding="utf-8"
                )
                st.info("Stop requested. The run will stop before the next item.")
        with col_refresh:
            if st.button("Refresh Status"):
                st.rerun()
        if output_text:
            st.code(output_text[-4000:], language="text")
        render_fresh_run_analysis(
            load_new_summary_rows(
                _completed_summary_path(state), _completed_previous_count(state)
            )
        )
        return True
    close_order_process_output(state)
    result = {
        "ok": returncode == 0,
        "exit_code": returncode,
        "command": " ".join(state["command"]),
        "output": output_text,
        "error_type": "ProcessError" if returncode else "",
        "error_message": f"Exited with status code {returncode}." if returncode else "",
    }
    render_command_result(result)
    render_fresh_run_analysis(
        load_new_summary_rows(
            _completed_summary_path(state), _completed_previous_count(state)
        )
    )
    st.session_state.pop("order_process", None)
    return False


def start_order_process(
    command: list[str],
    summary_path: Path,
    previous_row_count: int,
    stop_flag_path: Path,
    form_values: dict[str, object],
) -> None:
    """Start one order command in the background and remember its UI state."""
    from .streamlit_order_state import _profile_key_for_state
    stop_flag_path.parent.mkdir(parents=True, exist_ok=True)
    if stop_flag_path.exists():
        stop_flag_path.unlink()
    command = [*command, "--stop-flag", str(stop_flag_path)]
    output_path = order_output_path()
    state = start_cli_subprocess(command, output_path)
    state.update(
        {
            "summary_path": str(summary_path),
            "previous_row_count": previous_row_count,
            "profile_key": str(_profile_key_for_state(form_values)),
            "match_only": bool(form_values.get("match_only")),
            "stop_flag_path": str(stop_flag_path),
        }
    )
    st.session_state["order_process"] = state


def order_process_output(output_path: Path) -> str:
    """Return captured order-process output when available."""
    if not output_path.exists():
        return ""
    return output_path.read_text(encoding="utf-8", errors="replace")


def close_order_process_output(state: dict[str, object]) -> None:
    """Close the stored process output file handle if it is still open."""
    output_file = state.get("output_file")
    if output_file is None:
        return
    try:
        getattr(output_file, "close")()
    except Exception:
        pass
