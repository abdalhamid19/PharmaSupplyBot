"""Remove-cart tab rendering for the Streamlit GUI."""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from ..core.cart.cart_removal_items import DEFAULT_REMOVE_ITEMS_PATH
from .streamlit_shared import ARTIFACTS_DIR, load_csv_rows, REMOVE_ITEMS_DIR
from .streamlit_state import ensure_default_state_files, missing_state_profiles
from .streamlit_uploads import resolve_excel_path


# ============================================================================
# Form rendering for remove-cart tab
# ============================================================================


def remove_cart_form_values(app_config) -> tuple[bool, dict[str, object]]:
    """Return submitted remove-cart form values."""
    with st.form("remove_cart_form"):
        input_mode = st.radio(
            "Removal Excel source",
            ["Existing file", "Upload file", "Saved not matching manual review"],
            horizontal=True,
        )
        excel_path_str = existing_remove_excel_path(input_mode, remove_excel_options())
        upload = (
            st.file_uploader("Upload removal Excel", type=["xlsx"])
            if input_mode == "Upload file"
            else None
        )
        profile_mode = st.radio(
            "Run target", ["Single profile", "All profiles"], horizontal=True
        )
        profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0)
        execution_mode = st.selectbox(
            "Execution mode",
            ["auto", "api", "browser"],
            index=0,
            help="auto uses API when a safe contract exists, then falls back to browser.",
        )
        debug_browser = st.checkbox("Debug browser", value=False)
        item_workers = remove_cart_item_workers_field(app_config)
        submitted = st.form_submit_button("Remove Cart Items")
    return bool(submitted), {
        "input_mode": input_mode,
        "excel_path_str": excel_path_str,
        "upload": upload,
        "profile_mode": str(profile_mode),
        "profile_key": str(profile_key),
        "execution_mode": str(execution_mode),
        "debug_browser": bool(debug_browser),
        "item_workers": int(item_workers),
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


def remove_cart_item_workers_field(app_config) -> int:
    """Return the requested item-level worker count for one cart-removal run."""
    runtime = getattr(app_config, "runtime", None)
    configured = int(getattr(runtime, "item_workers", 1) or 1)
    return int(
        st.number_input(
            "Item workers",
            min_value=1,
            max_value=4,
            value=max(1, min(configured, 4)),
            help="Split this remove Excel across isolated Chromium workers.",
        )
    )


# ============================================================================
# Command building for remove-cart operations
# ============================================================================


def remove_cart_command(
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path | None,
) -> list[str]:
    """Return CLI command arguments for one remove-cart run."""
    command = _remove_cart_base_command(config_path, form_values, excel_path)
    command.extend(_remove_cart_profile_args(form_values))
    command.extend(_remove_cart_mode_args(form_values))
    command.extend(_remove_cart_worker_args(form_values))
    return command


def _remove_cart_base_command(
    config_path: Path, form_values: dict[str, object], excel_path: Path | None
) -> list[str]:
    """Return the base remove-cart command."""
    if _uses_saved_manual_review(form_values):
        return [
            "remove-cart",
            "--config",
            str(config_path),
            "--manual-review-scope",
            "saved-decisions",
            "--manual-decision",
            "not_matching",
        ]
    return ["remove-cart", "--config", str(config_path), "--excel", str(excel_path)]


def _remove_cart_profile_args(form_values: dict[str, object]) -> list[str]:
    """Return profile-related CLI arguments."""
    if form_values["profile_mode"] == "Single profile":
        return ["--profile", str(form_values["profile_key"])]
    return ["--all-profiles"]


def _remove_cart_mode_args(form_values: dict[str, object]) -> list[str]:
    """Return execution mode and debug CLI arguments."""
    args = []
    if form_values.get("debug_browser"):
        args.append("--debug-browser")
    args.extend(["--execution-mode", str(form_values.get("execution_mode", "auto"))])
    return args


def _remove_cart_worker_args(form_values: dict[str, object]) -> list[str]:
    """Return item workers CLI arguments."""
    item_workers = _form_int(form_values, "item_workers", 1)
    if item_workers > 1:
        return ["--item-workers", str(item_workers)]
    return []


def _uses_saved_manual_review(form_values: dict[str, object]) -> bool:
    """Check if using saved manual review mode."""
    return form_values.get("input_mode") == "Saved not matching manual review"


def _form_int(values: dict[str, object], key: str, default: int) -> int:
    """Return one integer form value with an empty-safe fallback."""
    value = values.get(key)
    if value is None or value == "":
        return default
    return int(value)


# ============================================================================
# Process management for remove-cart operations
# ============================================================================


def start_remove_cart_process(command: list[str], stop_flag_path: Path) -> None:
    """Start one remove-cart command and remember its process-control state."""
    stop_flag_path.parent.mkdir(parents=True, exist_ok=True)
    if stop_flag_path.exists():
        stop_flag_path.unlink()
    command = [*command, "--stop-flag", str(stop_flag_path)]
    output_path = remove_cart_output_path()
    from .views.streamlit_process import start_cli_subprocess
    state = start_cli_subprocess(command, output_path)
    state.update({"command": command, "stop_flag_path": str(stop_flag_path)})
    st.session_state["remove_cart_process"] = state


def remove_cart_output_path() -> Path:
    """Return a unique output path for the current remove-cart run."""
    output_dir = ARTIFACTS_DIR / "run_control"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"remove_cart_output_{int(time.time())}.log"


def remove_cart_stop_flag_path() -> Path:
    """Return the shared stop-request flag path for Streamlit remove-cart runs."""
    return ARTIFACTS_DIR / "run_control" / "remove_cart_stop.flag"


def remove_cart_process_output(output_path: Path) -> str:
    """Return captured remove-cart process output when available."""
    if not output_path.exists():
        return ""
    return output_path.read_text(encoding="utf-8", errors="replace")


def close_remove_cart_process_output(state: dict[str, object]) -> None:
    """Close the stored process output file handle if it is still open."""
    output_file = state.get("output_file")
    try:
        close = getattr(output_file, "close", None)
        if callable(close):
            close()
    except Exception:
        pass


# ============================================================================
# Main remove-cart tab rendering
# ============================================================================


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
    state = st.session_state.get("remove_cart_process")
    if not state:
        return False
    process = state["process"]
    returncode = process.poll()
    output_text = remove_cart_process_output(Path(state["output_path"]))
    if returncode is None:
        return _render_running_remove_cart(state, output_text, key_prefix)
    return _render_completed_remove_cart(state, returncode, output_text)


def _render_running_remove_cart(
    state: dict[str, object], output_text: str, key_prefix: str
) -> bool:
    """Render UI when remove-cart process is still running."""
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


def _render_completed_remove_cart(
    state: dict[str, object], returncode: int, output_text: str
) -> bool:
    """Render UI when remove-cart process has completed."""
    close_remove_cart_process_output(state)
    from .views.streamlit_process import render_command_result
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


__all__ = [
    "render_remove_cart_tab",
    "remove_cart_form_values",
    "remove_cart_command",
    "start_remove_cart_process",
    "remove_cart_output_path",
    "remove_cart_stop_flag_path",
]
