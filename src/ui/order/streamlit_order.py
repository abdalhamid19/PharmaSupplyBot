"""Order tab rendering for the Streamlit GUI - re-exports from split modules."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ...core.ordering.prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    is_prevented_items_excel_path,
)
from ..streamlit_uploads import resolve_excel_path

# Re-export from split modules
from .streamlit_order_form import (
    _int_form_value,
    _float_form_value,
    _append_optional_ai_text,
    order_output_path,
    order_stop_flag_path,
    run_control_dir,
    order_run_summary_csv_path,
    _latest_order_summary_path,
    prepare_order_state_files,
    target_profile_keys,
    _profile_key_for_state,
    _completed_summary_path,
    _completed_previous_count,
    order_form_values,
    order_form_fields,
    _order_form_values,
    _order_run_values,
    _extended_order_run_values,
)
from .streamlit_order_command import (
    order_command,
    _order_base_command,
    _order_profile_args,
    _order_debug_args,
    _order_execution_args,
    _order_worker_args,
    _order_discount_args,
    _order_item_range_args,
    _matching_risk_command_args,
    _order_execution_mode,
    _order_ai_command_args,
    _order_ai_provider_args,
    _order_ai_threshold_args,
)
from .streamlit_order_process import (
    render_running_order_controls,
    _render_running_order,
    _render_completed_order,
    start_order_process,
    order_process_output,
    close_order_process_output,
    render_fresh_run_analysis,
)


# ============================================================================
# Main order tab rendering
# ============================================================================


def render_order_tab(
    app_config, default_profile: str | None, config_path: Path
) -> None:
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
    excel_path = resolve_excel_path(
        form_values["excel_path_str"], form_values["upload"]
    )
    if excel_path is None:
        st.error("Please choose or upload an Excel file.")
        return
    prevented_items_path = Path(
        str(form_values.get("prevented_items_excel") or DEFAULT_PREVENTED_ITEMS_PATH)
    )
    if is_prevented_items_excel_path(excel_path, prevented_items_path):
        st.error(
            "`drugprevented.xlsx` is the prevented-items list, not an order sheet. "
            "Please choose the shortage/order Excel file."
        )
        return
    run_order_submission(
        app_config, default_profile, config_path, form_values, excel_path
    )


def run_order_submission(
    app_config,
    default_profile: str,
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> None:
    """Run one order submission and render its summary output."""
    fingerprint = order_submission_fingerprint(form_values, excel_path)
    if warn_if_duplicate_order_submission(fingerprint):
        return
    if not prepare_order_state_files(app_config, form_values):
        return
    start_valid_order_submission(
        default_profile, config_path, form_values, excel_path, fingerprint
    )


def start_valid_order_submission(
    default_profile: str,
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
    fingerprint: tuple[tuple[str, str], ...],
) -> None:
    """Start one validated background order process from Streamlit."""
    from ..streamlit_shared import csv_row_count

    summary_path = order_run_summary_csv_path(default_profile, form_values)
    previous_row_count = csv_row_count(summary_path)
    command = order_command(config_path, form_values, excel_path)
    stop_flag_path = order_stop_flag_path()
    start_order_process(
        command, summary_path, previous_row_count, stop_flag_path, form_values
    )
    st.session_state["last_order_submission_fingerprint"] = fingerprint
    st.success("Order flow started. Use Stop Order to stop after the current item.")
    st.rerun()


def order_submission_was_started(fingerprint: tuple[tuple[str, str], ...]) -> bool:
    """Return whether this Streamlit session already started the same order."""
    return st.session_state.get("last_order_submission_fingerprint") == fingerprint


def warn_if_duplicate_order_submission(fingerprint: tuple[tuple[str, str], ...]) -> bool:
    """Warn and return True when the same Streamlit order already started."""
    if not order_submission_was_started(fingerprint):
        return False
    st.warning(
        "This order submission was already started. Change the form to run it again."
    )
    return True


def order_submission_fingerprint(
    form_values: dict[str, object], excel_path: Path
) -> tuple[tuple[str, str], ...]:
    """Return a stable identity for one Streamlit order submission."""
    ignored = {"upload"}
    pairs = [("excel_path", str(excel_path))]
    pairs.extend(
        (key, str(value))
        for key, value in sorted(form_values.items())
        if key not in ignored
    )
    return tuple(pairs)


__all__ = [
    # Re-exports from form module
    "_int_form_value",
    "_float_form_value",
    "_append_optional_ai_text",
    "order_output_path",
    "order_stop_flag_path",
    "run_control_dir",
    "order_run_summary_csv_path",
    "_latest_order_summary_path",
    "prepare_order_state_files",
    "target_profile_keys",
    "_profile_key_for_state",
    "_completed_summary_path",
    "_completed_previous_count",
    "order_form_values",
    "order_form_fields",
    "_order_form_values",
    "_order_run_values",
    "_extended_order_run_values",
    # Re-exports from command module
    "order_command",
    "_order_base_command",
    "_order_profile_args",
    "_order_debug_args",
    "_order_execution_args",
    "_order_worker_args",
    "_order_discount_args",
    "_order_item_range_args",
    "_matching_risk_command_args",
    "_order_execution_mode",
    "_order_ai_command_args",
    "_order_ai_provider_args",
    "_order_ai_threshold_args",
    # Re-exports from process module
    "render_running_order_controls",
    "_render_running_order",
    "_render_completed_order",
    "start_order_process",
    "order_process_output",
    "close_order_process_output",
    "render_fresh_run_analysis",
    # Main entry points
    "render_order_tab",
    "run_order_submission",
    "start_valid_order_submission",
    "order_submission_was_started",
    "warn_if_duplicate_order_submission",
    "order_submission_fingerprint",
]
