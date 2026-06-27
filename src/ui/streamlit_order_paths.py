"""Path utilities for Streamlit order tab."""

from __future__ import annotations

import time
from pathlib import Path

from .streamlit_shared import ARTIFACTS_DIR, match_only_summary_csv_path, summary_csv_path


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
