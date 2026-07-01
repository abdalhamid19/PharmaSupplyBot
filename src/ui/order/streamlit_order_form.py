"""Order form value helpers and rendering for Streamlit."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ...core.ordering.prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    is_prevented_items_excel_path,
)
from ..fields.streamlit_ai_fields import ai_matching_fields
from ..fields.streamlit_excel_fields import excel_source_fields
from ..fields.streamlit_profile_fields import profile_run_fields_with_workers, OrderRunFields
from ..streamlit_shared import (
    ARTIFACTS_DIR,
    csv_row_count,
    match_only_summary_csv_path,
    summary_csv_path,
)
from ..streamlit_state import ensure_default_state_files, missing_state_profiles
from ..streamlit_uploads import resolve_excel_path


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


def _append_optional_ai_text(args: list[str], flag: str, value: object) -> None:
    """Append an optional text CLI flag."""
    text = str(value or "").strip()
    if text:
        args.extend([flag, text])


# ============================================================================
# Path utilities
# ============================================================================


def order_output_path() -> Path:
    """Return a unique output path for the current background order run."""
    return run_control_dir() / f"order_output_{int(__import__('time').time())}.log"


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
    """Return the profiles targeted by one order submission."""
    if form_values["profile_mode"] == "Single profile":
        return [str(form_values["profile_key"])]
    return list(app_config.profiles.keys())


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


def order_form_values(app_config) -> tuple[bool, dict[str, object]]:
    """Return the submitted order form values."""
    with st.form("order_form"):
        values = order_form_fields(app_config, DEFAULT_PREVENTED_ITEMS_PATH)
        submitted = st.form_submit_button("Run Order")
    return bool(submitted), values


def order_form_fields(
    app_config, prevented_items_path: Path | None = None
) -> dict[str, object]:
    """Return the order form field values."""
    input_mode, excel_path_str, upload = excel_source_fields()
    run_fields, item_workers = profile_run_fields_with_workers(app_config)
    values = _order_form_values(
        input_mode,
        excel_path_str,
        upload,
        run_fields,
        item_workers,
        prevented_items_path,
    )
    values.update(ai_matching_fields())
    return values


def _order_form_values(
    input_mode: str,
    excel_path_str: str,
    upload: object,
    run_fields: OrderRunFields,
    item_workers: int,
    prevented_items_path: Path | None,
) -> dict[str, object]:
    """Build serializable order form values from collected widget fields."""
    values = {
        "input_mode": input_mode,
        "excel_path_str": excel_path_str,
        "upload": upload,
        "item_workers": int(item_workers),
        "prevented_items_excel": str(
            prevented_items_path or DEFAULT_PREVENTED_ITEMS_PATH
        ),
    }
    values.update(_order_run_values(run_fields))
    return values


def _order_run_values(run_fields: OrderRunFields) -> dict[str, object]:
    """Build values related to the selected order run target/options."""
    profile_mode, profile_key, limit, debug_browser, resume, match_only = run_fields[:6]
    extended_vals = _extended_order_run_values(run_fields)
    execution_mode, high_disc, min_disc, start_item, end_item = extended_vals
    return {
        "profile_mode": profile_mode,
        "profile_key": profile_key,
        "limit": int(limit),
        "debug_browser": bool(debug_browser),
        "resume": bool(resume),
        "match_only": bool(match_only),
        "execution_mode": str(execution_mode),
        "highest_discount": bool(high_disc),
        "min_discount_percent": float(min_disc),
        "start_item": int(start_item),
        "end_item": int(end_item),
    }


def _extended_order_run_values(
    run_fields: OrderRunFields,
) -> tuple[str, bool, float, int, int]:
    """Return execution mode and discount controls with compatibility."""
    tail = run_fields[6:]
    if len(tail) == 2:
        high_disc, min_disc = tail
        return "auto", bool(high_disc), float(min_disc), 1, 0
    if len(tail) == 3:
        execution_mode, high_disc, min_disc = tail
        return str(execution_mode), bool(high_disc), float(min_disc), 1, 0
    execution_mode, high_disc, min_disc, start_item, end_item = tail
    return str(execution_mode), bool(high_disc), float(min_disc), int(start_item), int(end_item)


__all__ = [
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
]
