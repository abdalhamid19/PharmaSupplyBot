"""CLI subprocess helpers for manual review operations."""

from __future__ import annotations

import csv
import time
from pathlib import Path

import streamlit as st

from ..core.manual_review_corrections import write_corrected_review_csv
from .streamlit_process import start_cli_subprocess
from .streamlit_shared import ARTIFACTS_DIR


# ============ Remove Helpers ============

def start_not_matching_removal(rows: list[dict], run_dir: Path, st_module) -> None:
    """Write current not-matching rows and start remove-cart for the run profile."""
    path = write_not_matching_review_csv(rows, run_dir)
    command = manual_review_remove_command(Path("config.yaml"), run_dir, path)
    state = start_cli_subprocess(command, manual_review_remove_output_path())
    state.update({"command": command, "manual_review_csv": str(path)})
    st_module.session_state["remove_cart_process"] = state


def write_not_matching_review_csv(rows: list[dict], run_dir: Path) -> Path:
    """Persist edited not-matching rows as a remove-cart manual-review source."""
    selected = [row for row in rows if bool(row.get("not_matching"))]
    if not selected:
        raise ValueError("No not_matched manual-review rows selected.")
    path = run_dir / f"manual_review_not_matching_{run_dir.name}.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=sorted(_fieldnames(selected)))
        writer.writeheader()
        writer.writerows(selected)
    return path


def manual_review_remove_command(
    config_path: Path, run_dir: Path, manual_review_csv: Path
) -> list[str]:
    """Return the remove-cart command for current-run not-matching rows."""
    profile_key = run_dir.parent.name
    return [
        "remove-cart", "--config", str(config_path),
        "--profile", profile_key,
        "--from-manual-review", str(manual_review_csv),
        "--manual-decision", "not_matching",
    ]


def manual_review_remove_output_path() -> Path:
    """Return the process-output path for manual-review cart removal."""
    output_dir = ARTIFACTS_DIR / "run_control"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"manual_review_remove_{int(time.time())}.log"


def _fieldnames(rows: list[dict]) -> set[str]:
    names: set[str] = set()
    for row in rows:
        names.update(str(key) for key in row.keys())
    return names


# ============ Search Helpers ============

def start_corrected_item_search(rows: list[dict], run_dir: Path, st_module) -> None:
    """Write corrected rows and start order match-only search for them."""
    path = write_corrected_review_csv(rows, _corrected_review_path(run_dir))
    command = corrected_review_search_command(Path("config.yaml"), run_dir, path)
    state = start_cli_subprocess(command, corrected_review_search_output_path())
    state.update({"command": command, "manual_review_corrections": str(path)})
    st_module.session_state["manual_review_search_process"] = state


def corrected_review_search_command(config_path: Path, run_dir: Path, corrections_csv: Path) -> list[str]:
    """Return the order match-only command for corrected manual-review rows."""
    return [
        "order", "--config", str(config_path), "--profile", run_dir.parent.name,
        "--excel", str(corrections_csv), "--from-manual-review-corrections",
        str(corrections_csv), "--match-only", "--execution-mode", "auto"
    ]


def render_running_search_controls() -> bool:
    """Render controls and results for a background manual-review search process."""
    from .streamlit_process import render_command_result
    state = st.session_state.get("manual_review_search_process")
    if not state:
        return False
    process = state["process"]
    returncode = process.poll()
    output_text = _read_output_file(state.get("output_path"))
    if returncode is None:
        _render_running_status(output_text)
        return True
    _finish_search_process(state, returncode, output_text)
    return False


def _read_output_file(output_path_str):
    """Read output file content."""
    if not output_path_str:
        return ""
    output_path = Path(output_path_str)
    if not output_path.exists():
        return ""
    try:
        return output_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _render_running_status(output_text):
    """Render running status UI."""
    st.warning("Corrected items search is running.")
    if st.button("Refresh Search Status"):
        st.rerun()
    if output_text:
        st.code(output_text[-4000:], language="text")


def _finish_search_process(state, returncode, output_text):
    """Finish and clean up search process."""
    from .streamlit_process import render_command_result
    if "output_file" in state and not state["output_file"].closed:
        state["output_file"].close()
    render_command_result({
        "ok": returncode == 0, "exit_code": returncode,
        "command": " ".join(state["command"]), "output": output_text,
        "error_type": "ProcessError" if returncode else "",
        "error_message": f"Exited with status code {returncode}." if returncode else ""
    })
    st.session_state.pop("manual_review_search_process", None)


def corrected_review_search_output_path() -> Path:
    """Return the process-output path for manual-review corrected search."""
    output_dir = ARTIFACTS_DIR / "run_control"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"manual_review_search_{int(time.time())}.log"


def _corrected_review_path(run_dir: Path) -> Path:
    return run_dir / f"manual_review_corrections_{run_dir.name}.csv"


__all__ = [
    "start_not_matching_removal",
    "write_not_matching_review_csv",
    "manual_review_remove_command",
    "manual_review_remove_output_path",
    "start_corrected_item_search",
    "corrected_review_search_command",
    "render_running_search_controls",
    "corrected_review_search_output_path",
]
