"""Shared data and path helpers for the Streamlit GUI."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd
import streamlit as st


def inject_custom_css() -> None:
    """Inject custom CSS into the Streamlit app for a premium look."""
    css_path = Path(__file__).parent / "index.css"
    if css_path.exists():
        with css_path.open("r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


APP_TITLE = "PharmaSupplyBot"
DEFAULT_CONFIG_PATH = Path("state/config.yaml")
FALLBACK_CONFIG_PATH = Path("config.example.yaml")
INPUT_DIR = Path("data/input")
ORDER_ITEMS_DIR = INPUT_DIR / "order_items"
PREVENTED_ITEMS_DIR = INPUT_DIR / "prevented_items"
REMOVE_ITEMS_DIR = INPUT_DIR / "remove_items"
ARTIFACTS_DIR = Path("artifacts")
RUNNER_PATH = Path("run.py")


def sidebar_config_path() -> Path:
    """Return the selected YAML config path from the sidebar."""
    config_input = st.sidebar.text_input("Config path", str(DEFAULT_CONFIG_PATH))
    return Path(config_input).expanduser()


def resolved_streamlit_config_path(config_path: Path) -> Path:
    """Return the config path Streamlit should use, including the default example fallback."""
    if config_path.exists():
        return config_path
    if config_path == DEFAULT_CONFIG_PATH and FALLBACK_CONFIG_PATH.exists():
        return FALLBACK_CONFIG_PATH
    return config_path


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    """Return CSV rows from disk, or an empty list when the file is absent."""
    return _load_table_rows(path, "csv")


def load_xlsx_rows(path: Path) -> list[dict[str, str]]:
    """Return XLSX rows from disk, or an empty list when the file is absent."""
    return _load_table_rows(path, "xlsx")


def _load_table_rows(path: Path, table_format: str) -> list[dict[str, str]]:
    """Return table rows while invalidating cached data when the file changes."""
    try:
        file_statistics = path.stat()
    except FileNotFoundError:
        return []

    return _read_table_rows_cached(
        str(path.resolve()),
        file_statistics.st_mtime_ns,
        file_statistics.st_size,
        table_format,
    )


@st.cache_data(max_entries=128, show_spinner=False)
def _read_table_rows_cached(
    path_string: str,
    modified_time_ns: int,
    file_size: int,
    table_format: str,
) -> list[dict[str, str]]:
    """Read a table once for one file fingerprint and return ordered rows."""
    path = Path(path_string)
    reader = pd.read_csv if table_format == "csv" else pd.read_excel
    dataframe = reader(path).fillna("")
    return dataframe.to_dict(orient="records")


def csv_row_count(path: Path) -> int:
    """Return the number of data rows in a CSV artifact."""
    return len(load_csv_rows(path))


def load_new_summary_rows(path: Path, previous_row_count: int) -> list[dict[str, str]]:
    """Return only the summary rows appended after the recorded starting count."""
    if previous_row_count == 0:
        return load_csv_rows(path)
    try:
        file_statistics = path.stat()
    except FileNotFoundError:
        return []
    return _read_new_csv_rows_cached(
        str(path.resolve()),
        file_statistics.st_mtime_ns,
        file_statistics.st_size,
        previous_row_count,
    )


@st.cache_data(max_entries=128, show_spinner=False)
def _read_new_csv_rows_cached(
    path_string: str,
    modified_time_ns: int,
    file_size: int,
    previous_row_count: int,
) -> list[dict[str, str]]:
    """Parse only the appended CSV records while preserving pandas typing."""
    del modified_time_ns, file_size
    with Path(path_string).open("r", encoding="utf-8") as csv_file:
        records = (record for record in csv.reader(csv_file) if record)
        header = next(records, None)
        if header is None:
            return []
        for _ in range(previous_row_count):
            if next(records, None) is None:
                return []
        appended_records = list(records)
    if not appended_records:
        return []
    csv_text = io.StringIO()
    csv.writer(csv_text, lineterminator="\n").writerows([header, *appended_records])
    dataframe = pd.read_csv(io.StringIO(csv_text.getvalue())).fillna("")
    return dataframe.to_dict(orient="records")


def profile_selector_options() -> list[str]:
    """Return artifact profile directories for results browsing."""
    if not ARTIFACTS_DIR.exists():
        return ["wardany"]
    options = sorted(path.name for path in ARTIFACTS_DIR.iterdir() if path.is_dir())
    return options or ["wardany"]


def summary_csv_path(profile_key: str) -> Path:
    """Return the order-result summary CSV path for one profile."""
    return ARTIFACTS_DIR / profile_key / "order_item_summary.csv"


def summary_xlsx_path(profile_key: str) -> Path:
    """Return the order-result summary XLSX path for one profile."""
    return ARTIFACTS_DIR / profile_key / "order_item_summary.xlsx"


def match_only_summary_csv_path(profile_key: str) -> Path:
    """Return the dedicated match-only summary CSV path for one profile."""
    return ARTIFACTS_DIR / profile_key / "match_only_summary.csv"
