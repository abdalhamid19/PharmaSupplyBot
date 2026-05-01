"""Order tab rendering for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path
import time

import streamlit as st

from .streamlit_order_form import order_form_values
from .streamlit_process import render_command_result, start_cli_subprocess
from .streamlit_results import render_fresh_run_analysis
from .streamlit_shared import ARTIFACTS_DIR, csv_row_count, load_new_summary_rows, summary_csv_path
from .streamlit_state import (
    ensure_default_state_files,
    missing_state_profiles,
)
from .streamlit_uploads import resolve_excel_path


def render_order_tab(app_config, default_profile: str | None, config_path: Path) -> None:
    """Render order execution controls and fresh-run analysis."""
    st.subheader("Run Order")
    if not default_profile:
        st.warning("No profiles found in config.")
        return
    if render_running_order_controls():
        return
    submitted, form_values = order_form_values(app_config)
    if not submitted:
        return
    excel_path = resolve_excel_path(form_values["excel_path_str"], form_values["upload"])
    if excel_path is None:
        st.error("Please choose or upload an Excel file.")
        return
    run_order_submission(app_config, default_profile, config_path, form_values, excel_path)


def run_order_submission(
    app_config,
    default_profile: str,
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> None:
    """Run one order submission and render its summary output."""
    if not prepare_order_state_files(app_config, form_values):
        return
    summary_path = summary_csv_path(default_profile)
    previous_row_count = csv_row_count(summary_path)
    command = order_command(config_path, form_values, excel_path)
    start_order_process(command, summary_path, previous_row_count, order_stop_flag_path())
    st.success("Order flow started. Use Stop Order to stop after the current item.")
    st.rerun()


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
                Path(state["stop_flag_path"]).write_text("stop requested\n", encoding="utf-8")
                st.info("Stop requested. The run will stop before the next item.")
        with col_refresh:
            if st.button("Refresh Status"):
                st.rerun()
        if output_text:
            st.code(output_text[-4000:], language="text")
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
        load_new_summary_rows(Path(state["summary_path"]), int(state["previous_row_count"]))
    )
    st.session_state.pop("order_process", None)
    return False


def start_order_process(
    command: list[str],
    summary_path: Path,
    previous_row_count: int,
    stop_flag_path: Path,
) -> None:
    """Start one order command in the background and remember its UI state."""
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
            "stop_flag_path": str(stop_flag_path),
        }
    )
    st.session_state["order_process"] = state


def order_output_path() -> Path:
    """Return a unique output path for the current background order run."""
    return run_control_dir() / f"order_output_{int(time.time())}.log"


def order_stop_flag_path() -> Path:
    """Return the shared stop-request flag path for Streamlit order runs."""
    return run_control_dir() / "order_stop.flag"


def run_control_dir() -> Path:
    """Return the directory used for Streamlit process-control artifacts."""
    return ARTIFACTS_DIR / "run_control"


def order_process_output(output_path: Path) -> str:
    """Return captured order-process output when available."""
    if not output_path.exists():
        return ""
    return output_path.read_text(encoding="utf-8", errors="replace")


def close_order_process_output(state: dict[str, object]) -> None:
    """Close the stored process output file handle if it is still open."""
    output_file = state.get("output_file")
    try:
        output_file.close()
    except Exception:
        pass


def prepare_order_state_files(app_config, form_values: dict[str, object]) -> bool:
    """Ensure every target profile has a ready session-state file."""
    target_profiles = target_profile_keys(app_config, form_values)
    ensure_default_state_files(target_profiles)
    missing_profiles = missing_state_profiles(target_profiles)
    if not missing_profiles:
        return True
    missing_text = ", ".join(f"`{profile_key}`" for profile_key in missing_profiles)
    st.error(f"Missing session-state JSON for: {missing_text}")
    st.info("Upload `state/<profile>.json` from a machine where you already ran `py run.py auth`.")
    return False


def target_profile_keys(app_config, form_values: dict[str, object]) -> list[str]:
    """Return the profiles targeted by one order submission."""
    if form_values["profile_mode"] == "Single profile":
        return [str(form_values["profile_key"])]
    return list(app_config.profiles.keys())


def order_command(
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> list[str]:
    """Return the CLI command arguments for one order run."""
    command = ["order", "--config", str(config_path), "--excel", str(excel_path)]
    command.extend(["--limit", str(form_values["limit"])])
    if form_values["profile_mode"] == "Single profile":
        command.extend(["--profile", str(form_values["profile_key"])])
    else:
        command.append("--all-profiles")
    if form_values["debug_browser"]:
        command.append("--debug-browser")
    if form_values.get("resume"):
        command.append("--resume")
    if form_values.get("highest_discount"):
        command.extend(["--warehouse-mode", "max_discount"])
    min_discount_percent = float(form_values.get("min_discount_percent") or 0)
    if min_discount_percent > 0:
        command.extend(["--min-discount-percent", f"{min_discount_percent:g}"])
    return command
