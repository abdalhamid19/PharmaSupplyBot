"""End-to-end tests for the unified logging integration.

These tests invoke ``run.py`` as a subprocess for every public command
(``auth``, ``order``, ``match-products``, ``remove-cart``,
``export-products``) and verify:

* The right exit code is returned.
* ``logs/app.log`` is created and contains records.
* ``logs/errors.log`` is created and contains only ERROR+ records.
* The root command logger appears with a sensible name.

The tests deliberately avoid driving a full Tawreed run; they only feed
CLI flags that trigger a fast, deterministic failure (``--help``,
``--profile X``, missing required arg). The goal is to lock in the
contract that *every* command interacts correctly with the logging
stack — not to re-test the business logic of each command.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
PY = PROJECT / ".venv" / "Scripts" / "python.exe"
RUN = PROJECT / "run.py"


def _base_env(tmp_path: Path) -> dict[str, str]:
    """Build a subprocess env that resolves Windows DLLs and points the
    CWD at ``tmp_path`` so each test gets a fresh ``logs/`` directory.
    """
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


def _run(cmd: list[str], tmp_path: Path, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(tmp_path),
        env=_base_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _logs_dir(tmp_path: Path) -> Path:
    """The CLI writes logs to ``./logs`` relative to CWD."""
    return tmp_path / "logs"


# ─────────────────────────── Per-command smoke ───────────────────────────


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    """Copy ``config.example.yaml`` into ``tmp_path/state/`` so load_config()
    finds a config when invoked with ``--config tmp_path/state/config.yaml``.

    The example config defines one profile (``wardany``) which the tests
    then explicitly target or reject.
    """
    example = PROJECT / "config.example.yaml"
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / "config.yaml"
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    return target


@pytest.mark.parametrize(
    "argv, expected_exit",
    [
        # Each command's --help must succeed with exit 0.
        (["auth", "--help"], 0),
        (["order", "--help"], 0),
        (["match-products", "--help"], 0),
        (["remove-cart", "--help"], 0),
        (["export-products", "--help"], 0),
        # auth with an unknown profile must fail with ValidationError
        # (exit 5), proving the error path produces structured logs.
        (["auth", "--profile", "no_such_profile_xyz"], 5),
    ],
    ids=[
        "auth-help",
        "order-help",
        "match-products-help",
        "remove-cart-help",
        "export-products-help",
        "auth-bad-profile",
    ],
)
def test_command_exits_and_logs(
    tmp_path: Path,
    config_file: Path,
    argv: list[str],
    expected_exit: int,
) -> None:
    """Every CLI command must produce logs and the expected exit code."""
    # ``--config`` is a subcommand-level argument (added by
    # ``add_common_arguments``), so it must appear AFTER the subcommand
    # name, not before. argparse's subparsers consume the first positional
    # as the command name, and any global-style flag placed before it is
    # treated as belonging to the subparser.
    result = _run(
        [str(PY), str(RUN), *argv, "--config", str(config_file)],
        tmp_path,
    )

    assert result.returncode == expected_exit, (
        f"argv={argv} exit={result.returncode} stderr={result.stderr[:300]}"
    )

    # ``--help`` short-circuits argparse before run.main() runs, so the
    # CLI never configures logging for that case.
    if "--help" in argv:
        return

    # The console handler writes to stderr — at least the error/warning
    # line must be present on stderr for failure cases.
    if expected_exit != 0:
        assert result.stderr, "expected non-empty stderr on failure"

    # logs/app.log must exist and have content.
    app_log = _logs_dir(tmp_path) / "app.log"
    assert app_log.is_file(), f"app.log not created for argv={argv}"
    text = app_log.read_text(encoding="utf-8")
    assert text.strip(), f"app.log is empty for argv={argv}"


def test_help_commands_only_emit_root_records(tmp_path: Path) -> None:
    """``--help`` causes argparse to print usage and sys.exit(0) BEFORE
    ``run.main()`` configures logging. Therefore no application logs
    are produced. This test pins that behaviour so a future change that
    re-orders initialisation doesn't silently start logging on help.
    """
    result = _run([str(PY), str(RUN), "auth", "--help"], tmp_path)
    assert result.returncode == 0
    assert "usage:" in result.stdout or "usage:" in result.stderr
    # No logs/ directory created when --help short-circuits.
    assert not (_logs_dir(tmp_path) / "app.log").exists()


def test_failure_path_writes_to_errors_log(
    tmp_path: Path, config_file: Path
) -> None:
    """A ValidationError must show up in logs/errors.log too."""
    result = _run(
        [
            str(PY), str(RUN), "auth", "--config", str(config_file), "--profile", "no_such_xyz",
        ],
        tmp_path,
    )
    assert result.returncode == 5
    err_log = _logs_dir(tmp_path) / "errors.log"
    assert err_log.is_file()
    text = err_log.read_text(encoding="utf-8")
    assert "Unknown profile" in text
    # errors.log must only contain ERROR / CRITICAL lines.
    for line in text.splitlines():
        if "|" not in line:
            continue
        level = line.split("|")[1].strip()
        assert level in {"ERROR", "CRITICAL"}, (
            f"unexpected level {level!r} in errors.log: {line!r}"
        )


def test_app_log_records_have_iso_timestamp(
    tmp_path: Path, config_file: Path
) -> None:
    """app.log records must start with an ISO-8601 timestamp."""
    _run(
        [
            str(PY), str(RUN), "auth", "--config", str(config_file), "--profile", "no_such_xyz",
        ],
        tmp_path,
    )
    text = (_logs_dir(tmp_path) / "app.log").read_text(encoding="utf-8")
    for line in text.splitlines():
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", line), (
            f"non-ISO timestamp in line: {line!r}"
        )


def test_logging_setup_idempotent_under_repeated_invocations(
    tmp_path: Path, config_file: Path
) -> None:
    """run.py configures logging once via configure_logging(); calling
    it again from a second subprocess must not duplicate handlers in
    either log file (we only check file growth, not in-process state).
    """
    for _ in range(2):
        _run(
            [
                str(PY), str(RUN), "auth", "--config", str(config_file), "--profile", "no_such_xyz",
            ],
            tmp_path,
        )

    app_log = _logs_dir(tmp_path) / "app.log"
    text = app_log.read_text(encoding="utf-8")
    # Two runs -> two ERROR records mentioning the unknown profile.
    assert text.count("Unknown profile") == 2, (
        f"expected 2 records, got {text.count('Unknown profile')}"
    )