"""Streamlit GUI for Tawreed auth, ordering, and result review."""

from __future__ import annotations

import contextlib
import tempfile
import traceback
from pathlib import Path
import subprocess
import sys
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.config import load_config


APP_TITLE = "PharmaSupplyBot"
DEFAULT_CONFIG_PATH = Path("config.yaml")
INPUT_DIR = Path("input")
ARTIFACTS_DIR = Path("artifacts")
RUNNER_PATH = Path("run.py")


def main() -> None:
    """Render the Streamlit application."""
    load_dotenv()
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption("Tawreed authentication, order execution, and result review from one UI.")

    config_path = _sidebar_config_path()
    try:
        app_config = load_config(config_path)
    except Exception as error:
        st.error(f"Could not load config: {error}")
        st.stop()

    st.sidebar.success(f"Loaded config: `{config_path}`")
    profile_options = list(app_config.profiles.keys())
    default_profile = profile_options[0] if profile_options else None

    overview_tab, auth_tab, order_tab, results_tab = st.tabs(
        ["Overview", "Auth", "Order", "Results"]
    )
    with overview_tab:
        render_overview(app_config)
    with auth_tab:
        render_auth_tab(app_config, default_profile)
    with order_tab:
        render_order_tab(app_config, default_profile, config_path)
    with results_tab:
        render_results_tab(default_profile)


def _sidebar_config_path() -> Path:
    """Return the selected YAML config path from the sidebar."""
    config_input = st.sidebar.text_input("Config path", str(DEFAULT_CONFIG_PATH))
    return Path(config_input).expanduser()


def render_overview(app_config) -> None:
    """Render high-level project status and local environment details."""
    profiles = app_config.profiles
    input_files = sorted(INPUT_DIR.glob("*.xlsx")) if INPUT_DIR.exists() else []
    summary_rows = load_csv_rows(ARTIFACTS_DIR / "wardany" / "order_result_summary.csv")

    metrics = st.columns(4)
    metrics[0].metric("Profiles", len(profiles))
    metrics[1].metric("Input Excel Files", len(input_files))
    metrics[2].metric("Recent Summary Rows", len(summary_rows))
    metrics[3].metric("Submit Order", "On" if app_config.runtime.submit_order else "Off")

    st.subheader("Profiles")
    profile_rows = []
    for profile_key, profile in profiles.items():
        state_path = Path("state") / f"{profile_key}.json"
        profile_rows.append(
            {
                "profile": profile_key,
                "display_name": profile.display_name,
                "state_file": state_path.name,
                "state_exists": state_path.exists(),
            }
        )
    st.dataframe(pd.DataFrame(profile_rows), use_container_width=True, hide_index=True)

    st.subheader("Available Excel Files")
    if input_files:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "file": file.name,
                        "size_kb": round(file.stat().st_size / 1024, 1),
                    }
                    for file in input_files
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No Excel files found under `input/`.")

    if summary_rows:
        st.subheader("Latest Order Summary Rows")
        st.dataframe(pd.DataFrame(summary_rows[-10:]), use_container_width=True, hide_index=True)


def render_auth_tab(app_config, default_profile: str | None) -> None:
    """Render the auth workflow controls."""
    st.subheader("Interactive Login")
    if not default_profile:
        st.warning("No profiles found in config.")
        return

    with st.form("auth_form"):
        profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0)
        wait_seconds = st.number_input("Wait seconds", min_value=60, max_value=3600, value=600)
        submitted = st.form_submit_button("Start Auth Browser")

    if not submitted:
        return

    with st.spinner("Opening browser for login..."):
        result = run_cli_subprocess(
            [
                "auth",
                "--config",
                str(_sidebar_config_path()),
                "--profile",
                profile_key,
                "--wait-seconds",
                str(int(wait_seconds)),
            ]
        )
    render_command_result(result)


def render_order_tab(app_config, default_profile: str | None, config_path: Path) -> None:
    """Render order execution controls and fresh-run analysis."""
    st.subheader("Run Order")
    if not default_profile:
        st.warning("No profiles found in config.")
        return

    excel_options = [str(path) for path in sorted(INPUT_DIR.glob("*.xlsx"))] if INPUT_DIR.exists() else []
    with st.form("order_form"):
        input_mode = st.radio("Excel source", ["Existing file", "Upload file"], horizontal=True)
        excel_path_str = ""
        upload = None
        if input_mode == "Existing file":
            if excel_options:
                excel_path_str = st.selectbox("Excel file", excel_options, index=0)
            else:
                excel_path_str = st.text_input("Excel file path", "")
        else:
            upload = st.file_uploader("Upload Excel", type=["xlsx"])
        profile_mode = st.radio("Run target", ["Single profile", "All profiles"], horizontal=True)
        profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0)
        limit = st.number_input("Item limit", min_value=0, max_value=100000, value=50)
        debug_browser = st.checkbox("Debug browser", value=False)
        submitted = st.form_submit_button("Run Order")

    if not submitted:
        return

    excel_path = resolve_excel_path(excel_path_str, upload)
    if excel_path is None:
        st.error("Please choose or upload an Excel file.")
        return

    summary_path = summary_csv_path(default_profile)
    previous_row_count = csv_row_count(summary_path)
    command = [
        "order",
        "--config",
        str(config_path),
        "--excel",
        str(excel_path),
        "--limit",
        str(int(limit)),
    ]
    if profile_mode == "Single profile":
        command.extend(["--profile", profile_key])
    else:
        command.append("--all-profiles")
    if debug_browser:
        command.append("--debug-browser")

    with st.spinner("Running Tawreed order flow..."):
        result = run_cli_subprocess(command)
    render_command_result(result)

    new_rows = load_new_summary_rows(summary_path, previous_row_count)
    render_fresh_run_analysis(new_rows)


def render_results_tab(default_profile: str | None) -> None:
    """Render summary/result browsing tools."""
    st.subheader("Results")
    if not default_profile:
        st.warning("No profiles found in config.")
        return

    profile_key = st.selectbox("Artifacts profile", profile_selector_options(), index=0)
    summary_path = summary_csv_path(profile_key)
    summary_xlsx = summary_xlsx_path(profile_key)
    summary_rows = load_csv_rows(summary_path)
    summary_xlsx_rows = load_xlsx_rows(summary_xlsx)
    if not summary_rows and not summary_xlsx_rows:
        st.info(f"No summary files found for `{profile_key}`.")
    else:
        render_summary_views(profile_key, summary_path, summary_rows, summary_xlsx, summary_xlsx_rows)
        render_timing_metrics(summary_rows or summary_xlsx_rows)

    st.subheader("Recent Artifact Files")
    artifact_dir = ARTIFACTS_DIR / profile_key
    artifact_files = sorted(artifact_dir.glob("*"), key=lambda path: path.stat().st_mtime, reverse=True)
    if artifact_files:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "name": path.name,
                        "size_kb": round(path.stat().st_size / 1024, 1),
                    }
                    for path in artifact_files[:30]
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No artifact files found.")


def render_fresh_run_analysis(rows: list[dict[str, str]]) -> None:
    """Render metrics for one fresh execution window."""
    st.subheader("Fresh Run Analysis")
    if not rows:
        st.warning("No new summary rows were appended by this run.")
        return

    render_timing_metrics(rows)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_summary_views(
    profile_key: str,
    summary_csv: Path,
    csv_rows: list[dict[str, str]],
    summary_xlsx: Path,
    xlsx_rows: list[dict[str, str]],
) -> None:
    """Render order summary data from both CSV and XLSX artifacts when available."""
    st.markdown(f"**Summary profile:** `{profile_key}`")
    csv_col, xlsx_col = st.columns(2)
    with csv_col:
        st.caption(f"CSV: `{summary_csv}`")
    with xlsx_col:
        if summary_xlsx.exists():
            st.caption(f"XLSX: `{summary_xlsx}`")
        else:
            st.caption(f"XLSX: `{summary_xlsx}` (missing)")

    if summary_csv.exists() and summary_xlsx.exists():
        csv_time = summary_csv.stat().st_mtime
        xlsx_time = summary_xlsx.stat().st_mtime
        if xlsx_time < csv_time:
            st.warning("`order_result_summary.xlsx` is older than the CSV and may not reflect the latest run.")

    csv_tab, xlsx_tab = st.tabs(["CSV", "XLSX"])
    with csv_tab:
        if csv_rows:
            st.dataframe(pd.DataFrame(csv_rows[-100:]), use_container_width=True, hide_index=True)
        else:
            st.info("CSV summary is missing or empty.")
    with xlsx_tab:
        if xlsx_rows:
            st.dataframe(pd.DataFrame(xlsx_rows[-100:]), use_container_width=True, hide_index=True)
        else:
            st.info("XLSX summary is missing or empty.")


def render_timing_metrics(rows: list[dict[str, str]]) -> None:
    """Render elapsed-time metrics from populated summary rows."""
    elapsed_values = elapsed_seconds_values(rows)
    match_values = match_elapsed_seconds_values(rows)
    if not elapsed_values:
        st.info("No populated `elapsed_seconds` rows found.")
        return

    metrics = st.columns(4)
    metrics[0].metric("Rows", len(rows))
    metrics[1].metric("Average seconds", f"{sum(elapsed_values) / len(elapsed_values):.2f}")
    metrics[2].metric("Min seconds", f"{min(elapsed_values):.3f}")
    metrics[3].metric("Max seconds", f"{max(elapsed_values):.3f}")

    timing_breakdown = pd.DataFrame(
        [
            {
                "metric": "Average total seconds",
                "value": round(sum(elapsed_values) / len(elapsed_values), 3),
            },
            {
                "metric": "Average match seconds",
                "value": round(sum(match_values) / len(match_values), 3) if match_values else 0.0,
            },
            {
                "metric": "Max total seconds",
                "value": round(max(elapsed_values), 3),
            },
            {
                "metric": "Min total seconds",
                "value": round(min(elapsed_values), 3),
            },
        ]
    )
    top_rows = sorted(
        populated_elapsed_rows(rows),
        key=lambda row: float(row["elapsed_seconds"]),
        reverse=True,
    )[:15]

    left, right = st.columns(2)
    with left:
        st.markdown("**Timing summary**")
        st.dataframe(timing_breakdown, use_container_width=True, hide_index=True)
    with right:
        st.markdown("**Top slowest items**")
        top_dataframe = pd.DataFrame(top_rows)
        preferred_columns = [
            "item_code",
            "item_name",
            "status",
            "elapsed_seconds",
            "match_elapsed_seconds",
            "matched_product_name",
        ]
        visible_columns = [column for column in preferred_columns if column in top_dataframe.columns]
        st.dataframe(top_dataframe[visible_columns], use_container_width=True, hide_index=True)


def run_cli_subprocess(arguments: list[str]) -> dict[str, Any]:
    """Run the project CLI in a separate subprocess so Playwright is isolated from Streamlit."""
    command = [sys.executable, str(RUNNER_PATH), *arguments]
    try:
        completed = subprocess.run(
            command,
            cwd=str(Path.cwd()),
            text=True,
            capture_output=True,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "command": " ".join(command),
            "output": _combined_process_output(completed.stdout, completed.stderr),
            "error_type": "ProcessError" if completed.returncode else "",
            "error_message": f"Exited with status code {completed.returncode}." if completed.returncode else "",
        }
    except BaseException as error:  # noqa: BLE001
        return {
            "ok": False,
            "error_type": type(error).__name__,
            "error_message": exception_message(error),
            "command": " ".join(command),
            "output": "",
            "traceback": traceback.format_exc(),
        }


def render_command_result(result: dict[str, Any]) -> None:
    """Render one captured command result block."""
    if result["ok"]:
        st.success(f"Command completed. Exit code: {result.get('exit_code', 0)}")
    else:
        error_type = result.get("error_type", "Error")
        error_message = result.get("error_message", "Unknown failure")
        st.error(f"Command failed: {error_type}: {error_message}")
    if result.get("command"):
        st.caption(f"Command: `{result['command']}`")
    if result["output"]:
        st.code(result["output"], language="text")
    if result.get("traceback"):
        with st.expander("Traceback"):
            st.code(result["traceback"], language="text")


def resolve_excel_path(excel_path_str: str, uploaded_file) -> Path | None:
    """Return a usable Excel path from an existing file or uploaded content."""
    if uploaded_file is not None:
        suffix = Path(uploaded_file.name).suffix or ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            return Path(temp_file.name)
    if excel_path_str:
        return Path(excel_path_str)
    return None


def load_new_summary_rows(path: Path, previous_row_count: int) -> list[dict[str, str]]:
    """Return only the summary rows appended after the recorded starting count."""
    rows = load_csv_rows(path)
    return rows[previous_row_count:]


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    """Return CSV rows from disk, or an empty list when the file is absent."""
    if not path.exists():
        return []
    dataframe = pd.read_csv(path).fillna("")
    return dataframe.to_dict(orient="records")


def load_xlsx_rows(path: Path) -> list[dict[str, str]]:
    """Return XLSX rows from disk, or an empty list when the file is absent."""
    if not path.exists():
        return []
    dataframe = pd.read_excel(path).fillna("")
    return dataframe.to_dict(orient="records")


def csv_row_count(path: Path) -> int:
    """Return the number of data rows in a CSV artifact."""
    return len(load_csv_rows(path))


def exception_message(error: BaseException) -> str:
    """Return a readable exception message for Streamlit surfaces."""
    text = str(error).strip()
    if text:
        return text
    return repr(error)


def _combined_process_output(stdout: str, stderr: str) -> str:
    """Return one readable output block from subprocess stdout/stderr."""
    stdout_text = (stdout or "").strip()
    stderr_text = (stderr or "").strip()
    if stdout_text and stderr_text:
        return f"{stdout_text}\n\n[stderr]\n{stderr_text}"
    return stdout_text or stderr_text


def elapsed_seconds_values(rows: list[dict[str, str]]) -> list[float]:
    """Return parsed total elapsed seconds from rows that have the field populated."""
    values: list[float] = []
    for row in rows:
        raw_value = str(row.get("elapsed_seconds", "")).strip()
        if not raw_value:
            continue
        values.append(float(raw_value))
    return values


def match_elapsed_seconds_values(rows: list[dict[str, str]]) -> list[float]:
    """Return parsed matching-only elapsed seconds from rows that have the field populated."""
    values: list[float] = []
    for row in rows:
        raw_value = str(row.get("match_elapsed_seconds", "")).strip()
        if not raw_value:
            continue
        values.append(float(raw_value))
    return values


def populated_elapsed_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return rows that include a populated total elapsed-seconds field."""
    return [row for row in rows if str(row.get("elapsed_seconds", "")).strip()]


def profile_selector_options() -> list[str]:
    """Return artifact profile directories for results browsing."""
    if not ARTIFACTS_DIR.exists():
        return ["wardany"]
    options = sorted(path.name for path in ARTIFACTS_DIR.iterdir() if path.is_dir())
    return options or ["wardany"]


def summary_csv_path(profile_key: str) -> Path:
    """Return the order-result summary CSV path for one profile."""
    return ARTIFACTS_DIR / profile_key / "order_result_summary.csv"


def summary_xlsx_path(profile_key: str) -> Path:
    """Return the order-result summary XLSX path for one profile."""
    return ARTIFACTS_DIR / profile_key / "order_result_summary.xlsx"


if __name__ == "__main__":
    main()
