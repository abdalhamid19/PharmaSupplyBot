"""Streamlit helpers for searching corrected manual-review rows."""

from __future__ import annotations

from pathlib import Path
import time

from ..core.manual_review_corrections import write_corrected_review_csv
from .streamlit_process import start_cli_subprocess
from .streamlit_shared import ARTIFACTS_DIR


def start_corrected_item_search(rows: list[dict], run_dir: Path, st_module) -> None:
    """Write corrected rows and start order match-only search for them."""
    path = write_corrected_review_csv(rows, _corrected_review_path(run_dir))
    command = corrected_review_search_command(Path("config.yaml"), run_dir, path)
    state = start_cli_subprocess(command, corrected_review_search_output_path())
    state.update({"command": command, "manual_review_corrections": str(path)})
    st_module.session_state["manual_review_search_process"] = state


def corrected_review_search_command(
    config_path: Path, run_dir: Path, corrections_csv: Path
) -> list[str]:
    """Return the order match-only command for corrected manual-review rows."""
    return [
        "order", "--config", str(config_path),
        "--profile", run_dir.parent.name,
        "--excel", str(corrections_csv),
        "--from-manual-review-corrections", str(corrections_csv),
        "--match-only",
        "--execution-mode", "auto",
    ]


def corrected_review_search_output_path() -> Path:
    """Return the process-output path for manual-review corrected search."""
    output_dir = ARTIFACTS_DIR / "run_control"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"manual_review_search_{int(time.time())}.log"


def _corrected_review_path(run_dir: Path) -> Path:
    return run_dir / f"manual_review_corrections_{run_dir.name}.csv"
