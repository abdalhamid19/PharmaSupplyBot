"""Process management for remove-cart operations."""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from .streamlit_process import start_cli_subprocess
from .streamlit_shared import ARTIFACTS_DIR


def start_remove_cart_process(command: list[str], stop_flag_path: Path) -> None:
    """Start one remove-cart command and remember its process-control state."""
    stop_flag_path.parent.mkdir(parents=True, exist_ok=True)
    if stop_flag_path.exists():
        stop_flag_path.unlink()
    command = [*command, "--stop-flag", str(stop_flag_path)]
    output_path = remove_cart_output_path()
    state = start_cli_subprocess(command, output_path)
    state.update({"command": command, "stop_flag_path": str(stop_flag_path)})
    st.session_state["remove_cart_process"] = state


def remove_cart_output_path() -> Path:
    """Return a unique output path for the current remove-cart run."""
    output_dir = ARTIFACTS_DIR / "run_control"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"remove_cart_output_{int(time.time())}.log"


def remove_cart_stop_flag_path() -> Path:
    """Return the shared stop-request flag path for Streamlit remove-cart runs."""
    return ARTIFACTS_DIR / "run_control" / "remove_cart_stop.flag"


def remove_cart_process_output(output_path: Path) -> str:
    """Return captured remove-cart process output when available."""
    if not output_path.exists():
        return ""
    return output_path.read_text(encoding="utf-8", errors="replace")


def close_remove_cart_process_output(state: dict[str, object]) -> None:
    """Close the stored process output file handle if it is still open."""
    output_file = state.get("output_file")
    try:
        close = getattr(output_file, "close", None)
        if callable(close):
            close()
    except Exception:
        pass
