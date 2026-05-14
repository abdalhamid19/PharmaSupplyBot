"""Streamlit helpers for removing current-run not-matching review rows."""

from __future__ import annotations

import csv
from pathlib import Path
import time

from .streamlit_process import start_cli_subprocess
from .streamlit_shared import ARTIFACTS_DIR


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
        raise ValueError("No not_matching manual-review rows selected.")
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
