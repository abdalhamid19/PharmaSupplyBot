"""Remove-cart tab rendering for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .streamlit_shared import ARTIFACTS_DIR, load_csv_rows, REMOVE_ITEMS_DIR
from .streamlit_state import ensure_default_state_files, missing_state_profiles
from .streamlit_uploads import resolve_excel_path
from .streamlit_remove_cart_form import (
    remove_cart_form_values,
    existing_remove_excel_path,
    remove_excel_options,
    remove_cart_item_workers_field,
)
from .streamlit_remove_cart_command import (
    remove_cart_command,
    _uses_saved_manual_review,
)
from .streamlit_remove_cart_process import (
    start_remove_cart_process,
    remove_cart_output_path,
    remove_cart_stop_flag_path,
    remove_cart_process_output,
    close_remove_cart_process_output,
)


def render_remove_cart_tab(
    app_config, default_profile: str | None, config_path: Path
) -> None:
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
    excel_path = resolve_excel_path(
        form_values["excel_path_str"], form_values["upload"]
    )
    if excel_path is None and not _uses_saved_manual_review(form_values):
        st.error("Please choose or upload an Excel file.")
        return
    run_remove_cart_submission(app_config, config_path, form_values, excel_path)


def run_remove_cart_submission(
    app_config,
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path | None,
) -> None:
    """Start one remove-cart CLI process."""
    if not prepare_remove_cart_state_files(app_config, form_values):
        return
    command = remove_cart_command(config_path, form_values, excel_path)
    start_remove_cart_process(command, remove_cart_stop_flag_path())
    st.success("Cart-removal flow started.")
    st.rerun()


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


def remove_cart_target_profile_keys(
    app_config, form_values: dict[str, object]
) -> list[str]:
    """Return profiles targeted by one remove-cart submission."""
    if form_values["profile_mode"] == "Single profile":
        return [str(form_values["profile_key"])]
    return list(app_config.profiles.keys())


def render_running_remove_cart_controls(key_prefix: str = "remove_cart") -> bool:
    """Render controls and results for a background remove-cart process."""
    from .streamlit_process import render_command_result
    state = st.session_state.get("remove_cart_process")
    if not state:
        return False
    process = state["process"]
    returncode = process.poll()
    output_text = remove_cart_process_output(Path(state["output_path"]))
    if returncode is None:
        st.warning("Cart-removal flow is running.")
        col_stop, col_refresh = st.columns(2)
        with col_stop:
            if st.button("Stop Remove Cart", type="primary", key=f"{key_prefix}_stop"):
                Path(state["stop_flag_path"]).write_text(
                    "stop requested\n", encoding="utf-8"
                )
                st.info("Stop requested. Workers will stop before the next item.")
        with col_refresh:
            if st.button("Refresh Remove Status", key=f"{key_prefix}_refresh"):
                st.rerun()
        if output_text:
            st.code(output_text[-4000:], language="text")
        render_remove_cart_summary()
        return True
    close_remove_cart_process_output(state)
    render_command_result(
        {
            "ok": returncode == 0,
            "exit_code": returncode,
            "command": " ".join(state["command"]),
            "output": output_text,
            "error_type": "ProcessError" if returncode else "",
            "error_message": f"Exited with status code {returncode}."
            if returncode
            else "",
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
