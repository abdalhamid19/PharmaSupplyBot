"""Typed contracts for Streamlit subprocess lifecycle data."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Literal, TextIO, TypedDict


ProcessStatus = Literal["running", "completed", "failed"]


class ProcessState(TypedDict, total=False):
    """Runtime state shared by Streamlit background-process controls."""

    process: subprocess.Popen[str]
    output_file: TextIO
    output_path: Path
    command: list[str]
    stop_flag_path: str
    summary_path: str
    previous_row_count: int
    profile_key: str
    match_only: bool


class ProcessResult(TypedDict, total=False):
    """Normalized result shape used by completed Streamlit commands."""

    ok: bool
    exit_code: int
    command: str
    output: str
    error_type: str
    error_message: str
    traceback: str


__all__ = ["ProcessResult", "ProcessState", "ProcessStatus"]
