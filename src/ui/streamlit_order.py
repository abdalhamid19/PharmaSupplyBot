"""Order tab rendering for the Streamlit GUI."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st

from ..core.prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    is_prevented_items_excel_path,
)
from .streamlit_ai_fields import ai_matching_fields
from .streamlit_excel_fields import excel_source_fields
from .streamlit_profile_fields import profile_run_fields_with_workers, OrderRunFields
from .streamlit_shared import (
    ARTIFACTS_DIR,
    csv_row_count,
    load_new_summary_rows,
    match_only_summary_csv_path,
    summary_csv_path,
)
from .streamlit_state import ensure_default_state_files, missing_state_profiles
from .streamlit_uploads import resolve_excel_path


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
    return run_control_dir() / f"order_output_{int(time.time())}.log"


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
# Command building
# ============================================================================


def order_command(
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> list[str]:
    """Return the CLI command arguments for one order run."""
    command = _order_base_command(config_path, excel_path, form_values)
    command.extend(_order_profile_args(form_values))
    command.extend(_order_debug_args(form_values))
    command.extend(_order_execution_args(form_values))
    command.extend(_order_worker_args(form_values))
    command.extend(_order_discount_args(form_values))
    command.extend(_order_item_range_args(form_values))
    command.extend(_matching_risk_command_args(form_values))
    command.extend(_order_ai_command_args(form_values))
    return command


def _order_base_command(
    config_path: Path, excel_path: Path, form_values: dict[str, object]
) -> list[str]:
    """Return the base order command with config and excel."""
    command = ["order", "--config", str(config_path), "--excel", str(excel_path)]
    command.extend(["--limit", str(form_values["limit"])])
    return command


def _order_profile_args(form_values: dict[str, object]) -> list[str]:
    """Return profile-related CLI arguments."""
    if form_values["profile_mode"] == "Single profile":
        return ["--profile", str(form_values["profile_key"])]
    return ["--all-profiles"]


def _order_debug_args(form_values: dict[str, object]) -> list[str]:
    """Return debug and mode CLI arguments."""
    args = []
    if form_values["debug_browser"]:
        args.append("--debug-browser")
    if form_values.get("resume"):
        args.append("--resume")
    if form_values.get("match_only"):
        args.append("--match-only")
    return args


def _order_execution_args(form_values: dict[str, object]) -> list[str]:
    """Return execution mode CLI arguments."""
    return ["--execution-mode", _order_execution_mode(form_values)]


def _order_worker_args(form_values: dict[str, object]) -> list[str]:
    """Return item workers CLI arguments."""
    item_workers = _int_form_value(form_values, "item_workers", 1)
    return ["--item-workers", str(item_workers)]


def _order_discount_args(form_values: dict[str, object]) -> list[str]:
    """Return discount-related CLI arguments."""
    args = []
    if form_values.get("highest_discount"):
        args.extend(["--warehouse-mode", "max_discount"])
    min_discount = _float_form_value(form_values, "min_discount_percent", 0.0)
    if min_discount > 0:
        args.extend(["--min-discount-percent", f"{min_discount:g}"])
    prevented = str(form_values.get("prevented_items_excel") or "")
    if prevented:
        args.extend(["--prevented-items-excel", prevented])
    return args


def _order_item_range_args(form_values: dict[str, object]) -> list[str]:
    """Return item range (start/end) CLI arguments."""
    args = []
    start_item = _int_form_value(form_values, "start_item", 1)
    if start_item > 1:
        args.extend(["--start-item", str(start_item)])
    end_item = _int_form_value(form_values, "end_item", 0)
    if end_item > 0:
        args.extend(["--end-item", str(end_item)])
    return args


def _matching_risk_command_args(form_values: dict[str, object]) -> list[str]:
    """Return CLI arguments for safe or aggressive matching policy."""
    return [
        "--matching-risk-policy",
        str(form_values.get("matching_risk_policy") or "safe"),
        "--flagged-match-action",
        str(form_values.get("flagged_match_action") or "manual-review-only"),
    ]


def _order_execution_mode(form_values: dict[str, object]) -> str:
    """Return the fastest safe execution mode for the requested order run."""
    mode = str(form_values.get("execution_mode", "auto") or "auto")
    if form_values.get("match_only") and mode == "auto":
        return "api"
    return mode


def _order_ai_command_args(form_values: dict[str, object]) -> list[str]:
    """Return CLI arguments for optional live-order AI matching."""
    if not form_values.get("enable_order_ai"):
        return []
    args = ["--ai", *_order_ai_provider_args(form_values)]
    args.extend(_order_ai_threshold_args(form_values))
    _append_optional_ai_text(args, "--model", form_values.get("ai_model"))
    _append_optional_ai_text(args, "--review-model", form_values.get("ai_review_model"))
    return args


def _order_ai_provider_args(form_values: dict[str, object]) -> list[str]:
    """Return provider and policy CLI args for order AI."""
    return [
        "--provider",
        str(form_values.get("ai_provider") or "openrouter"),
        "--concurrency",
        str(_int_form_value(form_values, "ai_concurrency", 5)),
        "--ai-verify-policy",
        str(form_values.get("ai_verify_policy") or "score"),
        "--ai-search-policy",
        str(form_values.get("ai_search_policy") or "review-candidates"),
    ]


def _order_ai_threshold_args(form_values: dict[str, object]) -> list[str]:
    """Return confidence threshold CLI args for order AI."""
    accept = _float_form_value(form_values, "ai_accept_confidence", 0.9)
    review = _float_form_value(form_values, "ai_review_threshold", 0.95)
    return ["--ai-accept-confidence", f"{accept:g}", "--ai-review-threshold", f"{review:g}"]


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


# ============================================================================
# Background order process controls
# ============================================================================


def render_running_order_controls() -> bool:
    """Render controls for a background order process when one is active."""
    state = st.session_state.get("order_process")
    if not state:
        return False
    process = state["process"]
    returncode = process.poll()
    output_text = order_process_output(Path(state["output_path"]))
    if returncode is None:
        return _render_running_order(state, output_text)
    return _render_completed_order(state, returncode, output_text)


def _render_running_order(state: dict[str, object], output_text: str) -> bool:
    """Render UI when order process is still running."""
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


def _render_completed_order(
    state: dict[str, object], returncode: int, output_text: str
) -> bool:
    """Render UI when order process has completed."""
    close_order_process_output(state)
    result = {
        "ok": returncode == 0,
        "exit_code": returncode,
        "command": " ".join(state["command"]),
        "output": output_text,
        "error_type": "ProcessError" if returncode else "",
        "error_message": f"Exited with status code {returncode}." if returncode else "",
    }
    from .streamlit_process import render_command_result
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
    stop_flag_path.parent.mkdir(parents=True, exist_ok=True)
    if stop_flag_path.exists():
        stop_flag_path.unlink()
    command = [*command, "--stop-flag", str(stop_flag_path)]
    output_path = order_output_path()
    from .streamlit_process import start_cli_subprocess
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


def render_fresh_run_analysis(rows: list[dict[str, str]]) -> None:
    """Render metrics for one fresh execution window."""
    st.subheader("Fresh Run Analysis")
    if not rows:
        st.warning("No new summary rows were appended by this run.")
        return
    from .streamlit_timing_view import render_timing_metrics
    render_timing_metrics(rows)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


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
    if not prepare_order_state_files(app_config, form_values):
        return
    summary_path = order_run_summary_csv_path(default_profile, form_values)
    previous_row_count = csv_row_count(summary_path)
    command = order_command(config_path, form_values, excel_path)
    stop_flag_path = order_stop_flag_path()
    start_order_process(
        command, summary_path, previous_row_count, stop_flag_path, form_values
    )
    st.success("Order flow started. Use Stop Order to stop after the current item.")
    st.rerun()


__all__ = [
    "render_order_tab",
    "run_order_submission",
    "order_form_values",
    "order_form_fields",
    "order_command",
    "order_output_path",
    "order_stop_flag_path",
    "run_control_dir",
    "order_run_summary_csv_path",
    "prepare_order_state_files",
    "target_profile_keys",
    "render_running_order_controls",
    "start_order_process",
    "render_fresh_run_analysis",
]
