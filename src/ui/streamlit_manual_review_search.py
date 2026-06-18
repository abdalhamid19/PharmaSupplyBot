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


def render_running_search_controls() -> bool:
    """Render controls and results for a background manual-review search process."""
    import streamlit as st
    from .streamlit_process import render_command_result
    
    state = st.session_state.get("manual_review_search_process")
    if not state:
        return False
    process = state["process"]
    returncode = process.poll()
    
    output_path = Path(state["output_path"])
    output_text = ""
    if output_path.exists():
        try:
            output_text = output_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass

    if returncode is None:
        st.warning("Corrected items search is running.")
        if st.button("Refresh Search Status"):
            st.rerun()
        if output_text:
            st.code(output_text[-4000:], language="text")
        return True

    # Process finished
    if "output_file" in state and not state["output_file"].closed:
        state["output_file"].close()

    render_command_result(
        {
            "ok": returncode == 0,
            "exit_code": returncode,
            "command": " ".join(state["command"]),
            "output": output_text,
            "error_type": "ProcessError" if returncode else "",
            "error_message": f"Exited with status code {returncode}."
            if returncode
            else "",
        }
    )
    st.session_state.pop("manual_review_search_process", None)
    return False


def corrected_review_search_output_path() -> Path:
    """Return the process-output path for manual-review corrected search."""
    output_dir = ARTIFACTS_DIR / "run_control"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"manual_review_search_{int(time.time())}.log"


def _corrected_review_path(run_dir: Path) -> Path:
    return run_dir / f"manual_review_corrections_{run_dir.name}.csv"
