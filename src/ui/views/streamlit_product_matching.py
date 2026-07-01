"""Product matching tab for the Streamlit GUI."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st

from ..fields.streamlit_excel_fields import existing_excel_path, uploaded_excel_file
from ..streamlit_shared import ARTIFACTS_DIR, load_csv_rows
from ..streamlit_uploads import available_excel_options


# ============================================================================
# Product matching form handling
# ============================================================================


def product_matching_form(app_config, default_profile: str | None) -> tuple[bool, dict]:
    """Return submitted state and product matching form values."""
    with st.form("product_matching_form"):
        input_mode = st.radio(
            "Excel source", ["Existing file", "Upload file"], horizontal=True
        )
        excel_path = existing_excel_path(input_mode, available_excel_options())
        upload = uploaded_excel_file(input_mode)
        profile = st.selectbox(
            "Profile",
            list(app_config.profiles.keys()),
            index=_profile_index(app_config, default_profile),
        )
        limit = st.number_input("Item limit", min_value=0, max_value=100000, value=50)
        trace = st.checkbox("Trace", value=True)
        no_ai = st.checkbox("No AI", value=True)
        provider = st.selectbox(
            "AI provider", ["", "rotation", "groq", "opencode", "openrouter"]
        )
        model = st.text_input("AI model", value="")
        review_model = st.text_input("Review model", value="")
        concurrency = st.number_input("AI concurrency", min_value=1, max_value=20, value=5)
        submitted = st.form_submit_button("Run Product Matching")
    return bool(submitted), {
        "excel_path": excel_path,
        "upload": upload,
        "profile_key": profile,
        "limit": int(limit),
        "trace": bool(trace),
        "no_ai": bool(no_ai),
        "provider": str(provider),
        "model": str(model),
        "review_model": str(review_model),
        "concurrency": int(concurrency),
    }


def _profile_index(app_config, default_profile: str | None) -> int:
    """Return the index of the default profile in the profiles list."""
    profiles = list(app_config.profiles.keys())
    return profiles.index(default_profile) if default_profile in profiles else 0


# ============================================================================
# Product matching command building
# ============================================================================


def product_matching_command(
    config_path: Path, values: dict, excel_path: Path, output_path: Path
) -> list[str]:
    """Return CLI arguments for one product matching run."""
    command = [
        "match-products",
        "--config",
        str(config_path),
        "--profile",
        str(values["profile_key"]),
        "--excel",
        str(excel_path),
        "--output",
        str(output_path),
        "--limit",
        str(values["limit"]),
        "--concurrency",
        str(values["concurrency"]),
    ]
    if values["trace"]:
        command.append("--trace")
    if values["no_ai"]:
        command.append("--no-ai")
    command.extend(_optional_arg("--provider", values["provider"]))
    command.extend(_optional_arg("--model", values["model"]))
    command.extend(_optional_arg("--review-model", values["review_model"]))
    return command


def _optional_arg(name: str, value: object) -> list[str]:
    """Return optional CLI argument if value is non-empty."""
    text = str(value or "").strip()
    return [name, text] if text else []


# ============================================================================
# Product matching output handling
# ============================================================================


def render_running_matching_controls() -> bool:
    """Render a running or completed matching subprocess."""
    state = st.session_state.get("product_matching_process")
    if not state:
        return False
    returncode = state["process"].poll()
    output_text = order_process_output(Path(state["output_path"]))
    if returncode is None:
        return _render_running_matching(state, output_text)
    return _render_completed_matching(state, returncode, output_text)


def _render_running_matching(state: dict, output_text: str) -> bool:
    """Render UI when product matching is still running."""
    st.warning("Product matching is running.")
    if st.button("Refresh Matching Status"):
        st.rerun()
    if output_text:
        st.code(output_text[-4000:], language="text")
    render_matching_output_table(Path(state["output_csv"]))
    return True


def _render_completed_matching(state: dict, returncode: int, output_text: str) -> bool:
    """Render UI when product matching has completed."""
    close_order_process_output(state)
    from .streamlit_process import render_command_result
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
    from ..order.streamlit_order import run_control_dir
    return run_control_dir() / f"product_matching_output_{int(time.time())}.log"


def order_process_output(output_path: Path) -> str:
    """Return captured process output when available."""
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


def _matching_process_result(state: dict, returncode: int, output_text: str) -> dict:
    """Build the result dict for a completed matching process."""
    return {
        "ok": returncode == 0,
        "exit_code": returncode,
        "command": " ".join(state["command"]),
        "output": output_text,
        "error_type": "ProcessError" if returncode else "",
        "error_message": f"Exited with status code {returncode}." if returncode else "",
    }


# ============================================================================
# Main product matching tab rendering
# ============================================================================


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
    from ..streamlit_uploads import resolve_excel_path
    excel_path = resolve_excel_path(values["excel_path"], values["upload"])
    if excel_path is None:
        st.error("Please choose or upload an Excel file.")
        return
    output_path = matching_output_csv_path(str(values["profile_key"]))
    command = product_matching_command(config_path, values, excel_path, output_path)
    from .streamlit_process import start_cli_subprocess
    state = start_cli_subprocess(command, matching_output_log_path())
    state.update({"output_csv": str(output_path)})
    st.session_state["product_matching_process"] = state
    st.success("Product matching started.")
    st.rerun()


__all__ = ["render_product_matching_tab"]
