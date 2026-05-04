"""Remove-cart tab rendering for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path
import time

import streamlit as st

from .core.cart_removal_items import DEFAULT_REMOVE_ITEMS_PATH
from .streamlit_process import render_command_result, start_cli_subprocess
from .streamlit_shared import ARTIFACTS_DIR, REMOVE_ITEMS_DIR, load_csv_rows
from .streamlit_state import ensure_default_state_files, missing_state_profiles
from .streamlit_uploads import resolve_excel_path


def render_remove_cart_tab(app_config, default_profile: str | None, config_path: Path) -> None:
    """Render cart-removal execution controls."""
    st.subheader("Remove Cart Items")
    if not default_profile:
        st.warning("No profiles found in config.")
        return
    if render_running_remove_cart_controls():
        return
    submitted, form_values = remove_cart_form_values(app_config)
    if not submitted:
        return
    excel_path = resolve_excel_path(form_values["excel_path_str"], form_values["upload"])
    if excel_path is None:
        st.error("Please choose or upload an Excel file.")
        return
    run_remove_cart_submission(app_config, config_path, form_values, excel_path)


def remove_cart_form_values(app_config) -> tuple[bool, dict[str, object]]:
    """Return submitted remove-cart form values."""
    with st.form("remove_cart_form"):
        input_mode = st.radio(
            "Removal Excel source",
            ["Existing file", "Upload file"],
            horizontal=True,
        )
        excel_path_str = existing_remove_excel_path(input_mode, remove_excel_options())
        upload = (
            st.file_uploader("Upload removal Excel", type=["xlsx"])
            if input_mode == "Upload file"
            else None
        )
        profile_mode = st.radio("Run target", ["Single profile", "All profiles"], horizontal=True)
        profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0)
        debug_browser = st.checkbox("Debug browser", value=False)
        submitted = st.form_submit_button("Remove Cart Items")
    return bool(submitted), {
        "input_mode": input_mode,
        "excel_path_str": excel_path_str,
        "upload": upload,
        "profile_mode": str(profile_mode),
        "profile_key": str(profile_key),
        "debug_browser": bool(debug_browser),
    }


def existing_remove_excel_path(input_mode: str, excel_options: list[str]) -> str:
    """Return selected removal Excel path when existing-file mode is active."""
    if input_mode != "Existing file":
        return ""
    if excel_options:
        return str(st.selectbox("Removal Excel file", excel_options, index=0))
    return str(st.text_input("Removal Excel file path", str(DEFAULT_REMOVE_ITEMS_PATH)))


def remove_excel_options() -> list[str]:
    """Return existing cart-removal Excel files."""
    if not REMOVE_ITEMS_DIR.exists():
        return []
    return [str(path) for path in sorted(REMOVE_ITEMS_DIR.glob("*.xlsx"))]


def run_remove_cart_submission(
    app_config,
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> None:
    """Start one remove-cart CLI process."""
    if not prepare_remove_cart_state_files(app_config, form_values):
        return
    command = remove_cart_command(config_path, form_values, excel_path)
    output_path = remove_cart_output_path()
    state = start_cli_subprocess(command, output_path)
    state.update({"command": command})
    st.session_state["remove_cart_process"] = state
    st.success("Cart-removal flow started.")
    st.rerun()


def remove_cart_command(
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> list[str]:
    """Return CLI command arguments for one remove-cart run."""
    command = ["remove-cart", "--config", str(config_path), "--excel", str(excel_path)]
    if form_values["profile_mode"] == "Single profile":
        command.extend(["--profile", str(form_values["profile_key"])])
    else:
        command.append("--all-profiles")
    if form_values.get("debug_browser"):
        command.append("--debug-browser")
    return command


def prepare_remove_cart_state_files(app_config, form_values: dict[str, object]) -> bool:
    """Ensure every target profile has a ready session-state file."""
    target_profiles = remove_cart_target_profile_keys(app_config, form_values)
    ensure_default_state_files(target_profiles)
    missing_profiles = missing_state_profiles(target_profiles)
    if not missing_profiles:
        return True
    missing_text = ", ".join(f"`{profile_key}`" for profile_key in missing_profiles)
    st.error(f"Missing session-state JSON for: {missing_text}")
    return False


def remove_cart_target_profile_keys(app_config, form_values: dict[str, object]) -> list[str]:
    """Return profiles targeted by one remove-cart submission."""
    if form_values["profile_mode"] == "Single profile":
        return [str(form_values["profile_key"])]
    return list(app_config.profiles.keys())


def render_running_remove_cart_controls() -> bool:
    """Render controls and results for a background remove-cart process."""
    state = st.session_state.get("remove_cart_process")
    if not state:
        return False
    process = state["process"]
    returncode = process.poll()
    output_text = remove_cart_process_output(Path(state["output_path"]))
    if returncode is None:
        st.warning("Cart-removal flow is running.")
        if st.button("Refresh Remove Status"):
            st.rerun()
        if output_text:
            st.code(output_text[-4000:], language="text")
        return True
    close_remove_cart_process_output(state)
    render_command_result(
        {
            "ok": returncode == 0,
            "exit_code": returncode,
            "command": " ".join(state["command"]),
            "output": output_text,
            "error_type": "ProcessError" if returncode else "",
            "error_message": f"Exited with status code {returncode}." if returncode else "",
        }
    )
    render_remove_cart_summary()
    st.session_state.pop("remove_cart_process", None)
    return False


def render_remove_cart_summary() -> None:
    """Render the latest cart-removal summary when available."""
    summary_path = ARTIFACTS_DIR / "wardany" / "cart_removal_summary.csv"
    rows = load_csv_rows(summary_path)
    if rows:
        st.dataframe(rows[-20:], use_container_width=True, hide_index=True)


def remove_cart_output_path() -> Path:
    """Return a unique output path for the current remove-cart run."""
    output_dir = ARTIFACTS_DIR / "run_control"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"remove_cart_output_{int(time.time())}.log"


def remove_cart_process_output(output_path: Path) -> str:
    """Return captured remove-cart process output when available."""
    if not output_path.exists():
        return ""
    return output_path.read_text(encoding="utf-8", errors="replace")


def close_remove_cart_process_output(state: dict[str, object]) -> None:
    """Close the stored process output file handle if it is still open."""
    output_file = state.get("output_file")
    try:
        output_file.close()
    except Exception:
        pass
