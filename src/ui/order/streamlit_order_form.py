"""Order form value helpers and rendering for Streamlit.

The order form has two distinct kinds of widgets:

* Widgets that should react immediately to operator interaction
  (file uploaders, target checkboxes, advanced options) — these live
  outside ``st.form`` so the operator does not have to click "Run Order"
  for the uploader to even appear.
* A single submit button that kicks off the subprocess — this is the
  only thing that must live inside ``st.form`` so a rerun does not
  immediately trigger a run.

Both groups read/write a single ``st.session_state["order_form_values"]``
dict so the form value collection reads from one source of truth
regardless of which group the widget belongs to.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ...core.ordering.prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    is_prevented_items_excel_path,
)
from ..fields.streamlit_excel_fields import (
    render_excel_source_fields,
    resolve_order_excel_path,
    SOURCE_EXISTING,
)
from ..fields.streamlit_profile_fields import (
    profile_run_fields_with_workers,
    render_excel_target_sources,
)
from ..streamlit_shared import (
    ARTIFACTS_DIR,
    csv_row_count,
    match_only_summary_csv_path,
    summary_csv_path,
)
from ..streamlit_state import ensure_default_state_files, missing_state_profiles


# ============================================================================
# Form value helpers
# ============================================================================


def _int_form_value(form_values: dict[str, object], key: str, default: int) -> int:
    """Return one integer form value with a safe fallback."""
    return int(str(form_values.get(key, default) or default))


def _float_form_value(
    form_values: dict[str, object], key: str, default: float
) -> float:
    """Return one float form value with a safe fallback."""
    return float(str(form_values.get(key, default) or default))


# ============================================================================
# Path utilities
# ============================================================================


def order_output_path() -> Path:
    """Return a unique output path for the current background order run."""
    return run_control_dir() / f"order_output_{__import__('time').time_ns()}.log"


def order_stop_flag_path() -> Path:
    """Return the shared stop-request flag path for Streamlit order runs."""
    return run_control_dir() / "order_stop.flag"


def run_control_dir() -> Path:
    """Return the directory used for Streamlit process-control artifacts."""
    return ARTIFACTS_DIR / "run-control" / "order"


def order_run_summary_csv_path(
    profile_key: str, form_values: dict[str, object]
) -> Path:
    """Return the CSV summary watched for one Streamlit order run."""
    latest = _latest_order_summary_path(profile_key, bool(form_values.get("match_only")))
    if latest:
        return latest
    if form_values.get("match_only"):
        return match_only_summary_csv_path(profile_key)
    return summary_csv_path(profile_key)


def _latest_order_summary_path(profile_key: str, match_only: bool) -> Path | None:
    """Return the newest order summary from run folders."""
    label = "match_only_summary" if match_only else "order_item_summary"
    paths = sorted((ARTIFACTS_DIR / "order" / profile_key).glob(f"*/{label}_*.csv"))
    return paths[-1] if paths else None


# ============================================================================
# State file preparation
# ============================================================================


def prepare_order_state_files(app_config, form_values: dict[str, object]) -> bool:
    """Ensure every target profile has a ready session-state file."""
    target_profiles = target_profile_keys(app_config, form_values)
    ensure_default_state_files(target_profiles)
    missing_profiles = missing_state_profiles(target_profiles)
    if not missing_profiles:
        return True
    missing_text = ", ".join(f"`{profile_key}`" for profile_key in missing_profiles)
    st.error(f"Missing session-state JSON for: {missing_text}")
    st.info(
        "Upload `state/<profile>.json` from a machine where you already ran `py run.py auth`."
    )
    return False


def target_profile_keys(app_config, form_values: dict[str, object]) -> list[str]:
    """Return the Tawreed profile keys targeted by one order submission."""
    selected_targets = form_values.get("selected_targets") or ()
    profile_keys = [
        token.split(":", 1)[1]
        for token in selected_targets
        if isinstance(token, str) and token.startswith("profile:")
    ]
    if profile_keys:
        return profile_keys
    profile_key = str(form_values.get("profile_key") or "")
    if profile_key:
        return [profile_key]
    return list(app_config.profiles.keys())


def selected_excel_targets(form_values: dict[str, object]) -> list[str]:
    """Return the Excel-target keys targeted by one order submission."""
    selected_targets = form_values.get("selected_targets") or ()
    return [
        token.split(":", 1)[1]
        for token in selected_targets
        if isinstance(token, str) and token.startswith("excel-target:")
    ]


def _profile_key_for_state(form_values: dict[str, object]) -> str:
    """Return the single profile key used for result watching."""
    return str(form_values.get("profile_key") or "wardany")


def _completed_summary_path(state: dict[str, object]) -> Path:
    """Return the completed run summary path for process rendering."""
    latest = _latest_order_summary_path(
        str(state.get("profile_key", "wardany")), bool(state.get("match_only"))
    )
    return latest or Path(str(state["summary_path"]))


def _completed_previous_count(state: dict[str, object]) -> int:
    """Return previous row count only when the watched path did not change."""
    completed = _completed_summary_path(state)
    if completed == Path(str(state["summary_path"])):
        return int(state["previous_row_count"])
    return 0


# ============================================================================
# Order form helpers
# ============================================================================


def order_form_values(
    app_config, config_path: Path | None = None
) -> tuple[bool, dict[str, object]]:
    """Return the submitted order form values.

    Every input widget lives outside ``st.form`` so the operator gets
    immediate feedback. The form block is a thin wrapper that only
    exposes the "Run Order" submit button.
    """
    render_order_inputs(app_config, config_path=config_path)
    values = _collect_form_values()
    with st.form("order_form"):
        submitted = st.form_submit_button("Run Order")
    return bool(submitted), values


def render_order_inputs(app_config, config_path: Path | None = None) -> None:
    """Render every input widget outside of ``st.form``."""
    st.subheader("Order inputs")
    render_excel_source_fields()
    st.divider()
    profile_run_fields_with_workers(app_config, config_path=config_path)
    excel_target_uploads = render_excel_target_sources(app_config)
    if excel_target_uploads:
        st.session_state["order_form_excel_target_uploads"] = excel_target_uploads
    st.divider()


def _collect_form_values() -> dict[str, object]:
    """Aggregate widget state from ``st.session_state`` into a flat dict."""
    selected = st.session_state.get("excel_target_selected_targets") or ()
    profile_key = next(
        (
            token.split(":", 1)[1]
            for token in selected
            if isinstance(token, str) and token.startswith("profile:")
        ),
        str(st.session_state.get("order_form_primary_profile") or ""),
    )
    item_workers = st.session_state.get("order_form_item_workers", 1)
    uploads = st.session_state.get("order_form_excel_target_uploads") or {}
    advanced = st.session_state.get("order_form_advanced") or {}

    return {
        "input_mode": st.session_state.get(
            "order_excel_source_mode", SOURCE_EXISTING
        ),
        "excel_path_str": st.session_state.get("order_excel_path", ""),
        "upload": st.session_state.get("order_excel_upload"),
        "selected_targets": tuple(selected),
        "profile_key": profile_key,
        "profile_mode": _profile_mode(selected),
        "item_workers": int(item_workers),
        "limit": int(advanced.get("limit", 0)),
        "debug_browser": bool(advanced.get("debug_browser", False)),
        "resume": bool(advanced.get("resume", False)),
        "match_only": bool(advanced.get("match_only", False)),
        "execution_mode": str(advanced.get("execution_mode", "auto")),
        "highest_discount": bool(advanced.get("highest_discount", False)),
        "min_discount_percent": float(advanced.get("min_discount_percent", 0.0)),
        "start_item": int(advanced.get("start_item", 1)),
        "end_item": int(advanced.get("end_item", 0)),
        "prevented_items_excel": str(DEFAULT_PREVENTED_ITEMS_PATH),
        "excel_target_uploads": dict(uploads),
    }


def _profile_mode(selected: tuple[str, ...]) -> str:
    has_profile = any(isinstance(t, str) and t.startswith("profile:") for t in selected)
    if not has_profile:
        return "Excel targets only"
    return "Single profile" if len([t for t in selected if t.startswith("profile:")]) == 1 else "Multi"


__all__ = [
    "_int_form_value",
    "_float_form_value",
    "order_output_path",
    "order_stop_flag_path",
    "run_control_dir",
    "order_run_summary_csv_path",
    "_latest_order_summary_path",
    "prepare_order_state_files",
    "target_profile_keys",
    "selected_excel_targets",
    "_profile_key_for_state",
    "_completed_summary_path",
    "_completed_previous_count",
    "order_form_values",
    "render_order_inputs",
    "resolve_order_excel_path",
]