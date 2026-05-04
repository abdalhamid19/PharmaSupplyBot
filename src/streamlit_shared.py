"""Shared data and path helpers for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


APP_TITLE = "PharmaSupplyBot"
DEFAULT_CONFIG_PATH = Path("config.yaml")
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
    return _load_table_rows(path, pd.read_csv)


def load_xlsx_rows(path: Path) -> list[dict[str, str]]:
    """Return XLSX rows from disk, or an empty list when the file is absent."""
    return _load_table_rows(path, pd.read_excel)


def _load_table_rows(path: Path, reader) -> list[dict[str, str]]:
    """Return table rows from one artifact path using the provided pandas reader."""
    if not path.exists():
        return []
    dataframe = reader(path).fillna("")
    return dataframe.to_dict(orient="records")


def csv_row_count(path: Path) -> int:
    """Return the number of data rows in a CSV artifact."""
    return len(load_csv_rows(path))


def load_new_summary_rows(path: Path, previous_row_count: int) -> list[dict[str, str]]:
    """Return only the summary rows appended after the recorded starting count."""
    return load_csv_rows(path)[previous_row_count:]


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
