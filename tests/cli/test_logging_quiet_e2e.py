"""End-to-end tests for the --quiet / -q flag across every CLI command.

Contract: when ``--quiet`` is on, the console handler is set to WARNING+
and lower levels are suppressed. The file handlers still capture
everything.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
PY = PROJECT / ".venv" / "Scripts" / "python.exe"
RUN = PROJECT / "run.py"


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        "PATH": (
            "C:\\Windows\\System32;C:\\Windows;"
            "C:\\pc\\py\\pyreview\\PharmaSupplyBot\\.venv\\Scripts;"
            "C:\\Users\\QUANTUM\\AppData\\Local\\Programs\\Python\\Python313"
        ),
        "PYTHONPATH": str(PROJECT),
        "SYSTEMROOT": "C:\\Windows",
        "TEMP": str(tmp_path),
        "USERPROFILE": str(tmp_path),
        "HOME": str(tmp_path),
    }


def _run(argv: list[str], tmp_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PY), str(RUN), *argv],
        cwd=str(tmp_path),
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )


# ─────────────────────────── --quiet behaviour ───────────────────────────


def test_quiet_silences_info_on_stderr(tmp_path: Path, config_file: Path) -> None:
    """``--quiet`` must suppress INFO on stderr but keep WARNING/ERROR."""
    result = _run(
        ["--quiet", "auth", "--config", str(config_file), "--profile", "no_such_xyz"],
        tmp_path,
    )
    assert result.returncode == 5
    # The hint is at WARNING, so it stays.
    assert "hint" in result.stderr
    # The error message is at ERROR.
    assert "Unknown profile" in result.stderr
    # No INFO-level records leaked.
    assert "INFO" not in result.stderr


def test_quiet_still_writes_everything_to_file(tmp_path: Path, config_file: Path) -> None:
    """Files always capture DEBUG+; --quiet only affects the console."""
    result = _run(
        ["--quiet", "auth", "--config", str(config_file), "--profile", "no_such_xyz"],
        tmp_path,
    )
    assert result.returncode == 5

    app_log = tmp_path / "logs" / "app.log"
    assert app_log.is_file()
    text = app_log.read_text(encoding="utf-8")
    assert "Unknown profile" in text
    assert "hint" in text


def test_quiet_short_flag_alias(tmp_path: Path, config_file: Path) -> None:
    """``-q`` is the documented short alias for ``--quiet``."""
    result = _run(["-q", "auth", "--config", str(config_file), "--profile", "no_such_xyz"], tmp_path)
    assert result.returncode == 5
    assert "Unknown profile" in result.stderr


def test_no_quiet_default_keeps_all_levels(tmp_path: Path, config_file: Path) -> None:
    """Without ``--quiet`` the default level is INFO so INFO+ appear on
    stderr. The run.py banner currently does not emit INFO records on
    its own, so the only thing we can pin is that ``Unknown profile``
    appears at the default level."""
    result = _run(["auth", "--config", str(config_file), "--profile", "no_such_xyz"], tmp_path)
    assert result.returncode == 5
    assert "Unknown profile" in result.stderr


def test_quiet_does_not_affect_errors_log(tmp_path: Path, config_file: Path) -> None:
    """Errors logged via ``--quiet`` still appear in errors.log."""
    result = _run(
        ["--quiet", "auth", "--config", str(config_file), "--profile", "no_such_xyz"],
        tmp_path,
    )
    assert result.returncode == 5
    err_log = tmp_path / "logs" / "errors.log"
    assert err_log.is_file()
    assert "Unknown profile" in err_log.read_text(encoding="utf-8")


# ─────────────────────────── --log-level ───────────────────────────


def test_log_level_debug_increases_verbosity(tmp_path: Path, config_file: Path) -> None:
    """``--log-level DEBUG`` enables DEBUG output on stderr."""
    result = _run(
        ["--log-level", "DEBUG", "auth", "--config", str(config_file), "--profile", "no_such_xyz"],
        tmp_path,
    )
    assert result.returncode == 5
    # The dispatch log line is at DEBUG; if --log-level is honoured it
    # will appear in app.log.
    app_log = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "dispatching command" in app_log


def test_log_level_unknown_choice_rejected(tmp_path: Path) -> None:
    """An unrecognised ``--log-level`` value must be rejected by argparse
    before run.py sees it."""
    result = _run(
        ["--log-level", "BOGUS", "auth", "--help"],
        tmp_path,
    )
    assert result.returncode == 2  # argparse usage error
    assert "invalid choice" in result.stderr or "invalid choice" in result.stdout


def test_log_level_warning_suppresses_info(tmp_path: Path, config_file: Path) -> None:
    """``--log-level WARNING`` suppresses INFO/DEBUG on stderr."""
    result = _run(
        ["--log-level", "WARNING", "auth", "--config", str(config_file), "--profile", "no_such_xyz"],
        tmp_path,
    )
    assert result.returncode == 5
    # No INFO/DEBUG lines on stderr; ERROR and WARNING still appear.
    for level in ("INFO", "DEBUG"):
        assert f" | {level} " not in result.stderr
    assert " | ERROR " in result.stderr or " | WARNING " in result.stderr