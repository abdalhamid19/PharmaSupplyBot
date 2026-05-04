"""Subprocess execution helpers for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import traceback

import streamlit as st

from .streamlit_shared import RUNNER_PATH
from .streamlit_subprocess_env import merged_env


def run_cli_subprocess(arguments: list[str], env_overrides: dict[str, str] | None = None) -> dict[str, object]:
    """Run the project CLI in a subprocess so Playwright is isolated from Streamlit."""
    command = cli_command(arguments)
    try:
        completed = _completed_process(command, merged_env(env_overrides))
        return _process_result(command, completed.returncode, completed.stdout, completed.stderr)
    except BaseException as error:  # noqa: BLE001
        return _failed_process_result(command, error)


def start_cli_subprocess(
    arguments: list[str],
    output_path: Path,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, object]:
    """Start the project CLI in the background and stream output to a file."""
    command = cli_command(arguments)
    output_file = output_stream(output_path)
    process = subprocess.Popen(
        command,
        cwd=working_directory(),
        env=merged_env(env_overrides),
        text=True,
        stdout=output_file,
        stderr=subprocess.STDOUT,
    )
    return {
        "process": process,
        "output_file": output_file,
        "output_path": output_path,
        "command": command,
    }


def cli_command(arguments: list[str]) -> list[str]:
    """Return the Python command used to invoke the project CLI."""
    return [sys.executable, str(RUNNER_PATH), *arguments]


def output_stream(output_path: Path):
    """Return the writable output file used for a background CLI run."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path.open("w", encoding="utf-8", errors="replace")


def working_directory() -> str:
    """Return the current working directory for spawned subprocesses."""
    return str(Path.cwd())


def _completed_process(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run one completed subprocess and return the captured result."""
    return subprocess.run(
        command,
        cwd=working_directory(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _process_result(
    command: list[str],
    returncode: int,
    stdout: str,
    stderr: str,
) -> dict[str, object]:
    """Return the normalized result structure for one completed subprocess."""
    return {
        "ok": returncode == 0,
        "exit_code": returncode,
        "command": " ".join(command),
        "output": combined_process_output(stdout, stderr),
        "error_type": "ProcessError" if returncode else "",
        "error_message": f"Exited with status code {returncode}." if returncode else "",
    }


def _failed_process_result(command: list[str], error: BaseException) -> dict[str, object]:
    """Return the normalized result structure for one subprocess-start failure."""
    return {
        "ok": False,
        "error_type": type(error).__name__,
        "error_message": exception_message(error),
        "command": " ".join(command),
        "output": "",
        "traceback": traceback.format_exc(),
    }


def render_command_result(result: dict[str, object]) -> None:
    """Render one captured command result block."""
    if bool(result["ok"]):
        st.success(f"Command completed. Exit code: {result.get('exit_code', 0)}")
    else:
        st.error(f"Command failed: {result.get('error_type')}: {result.get('error_message')}")
    if result.get("command"):
        st.caption(f"Command: `{result['command']}`")
    if result.get("output"):
        st.code(str(result["output"]), language="text")
    if result.get("traceback"):
        with st.expander("Traceback"):
            st.code(str(result["traceback"]), language="text")


def exception_message(error: BaseException) -> str:
    """Return a readable exception message for Streamlit surfaces."""
    text = str(error).strip()
    return text if text else repr(error)


def combined_process_output(stdout: str, stderr: str) -> str:
    """Return one readable output block from subprocess stdout/stderr."""
    stdout_text = (stdout or "").strip()
    stderr_text = (stderr or "").strip()
    if stdout_text and stderr_text:
        return f"{stdout_text}\n\n[stderr]\n{stderr_text}"
    return stdout_text or stderr_text
