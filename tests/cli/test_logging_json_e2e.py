"""End-to-end tests for --json-log-records output across every CLI command.

When ``--json-log-records`` is set, every log record must be emitted as a
single-line JSON object that decodes without error and contains the
schema documented in :mod:`src.cli.logging_setup`.
"""

from __future__ import annotations

import json
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




def _config_file(tmp_path: Path) -> Path:
    """Copy config.example.yaml into tmp_path/state/ so load_config finds it."""
    example = PROJECT / "config.example.yaml"
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / "config.yaml"
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _run(argv: list[str], tmp_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PY), str(RUN), *argv],
        cwd=str(tmp_path),
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )


# ─────────────────────────── JSON schema ───────────────────────────


REQUIRED_FIELDS = {"ts", "level", "logger", "message"}


def _assert_json_record(line: str) -> dict:
    """Parse one log line as JSON and assert it has the schema we promise."""
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as e:
        pytest.fail(f"line is not valid JSON: {line!r} ({e})")
    missing = REQUIRED_FIELDS - payload.keys()
    assert not missing, f"missing required JSON fields: {missing} in {payload}"
    assert payload["level"] in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    return payload


# ─────────────────────────── Per-command JSON output ───────────────────────────


def test_json_logs_failure_emits_valid_json(
    tmp_path: Path, config_file: Path
) -> None:
    """A ValidationError must be emitted on stderr as parseable JSON."""
    result = _run(
        [
            "--json-log-records",
            "auth", "--config", str(config_file), "--profile", "no_such_xyz",
        ],
        tmp_path,
    )
    assert result.returncode == 5

    stderr_lines = [l for l in result.stderr.splitlines() if l.strip()]
    assert stderr_lines, "expected at least one JSON record on stderr"

    # First record should be the ERROR one.
    payload = _assert_json_record(stderr_lines[0])
    assert payload["level"] == "ERROR"
    assert payload["exit_code"] == 5  # extra field from run.py
    assert "Unknown profile" in payload["message"]


def test_json_logs_hint_appears_on_stderr(
    tmp_path: Path, config_file: Path
) -> None:
    """The WARNING 'hint' record should also be JSON."""
    result = _run(
        [
            "--json-log-records",
            "auth", "--config", str(config_file), "--profile", "no_such_xyz",
        ],
        tmp_path,
    )
    assert result.returncode == 5

    records = [
        _assert_json_record(line)
        for line in result.stderr.splitlines()
        if line.strip()
    ]
    levels = {r["level"] for r in records}
    assert "ERROR" in levels
    assert "WARNING" in levels


def test_json_logs_records_have_logger_name(
    tmp_path: Path, config_file: Path
) -> None:
    """Every JSON record must carry the ``logger`` field with the dotted
    module path. After stage 4 the root command logger is ``__main__``.
    """
    result = _run(
        [
            "--json-log-records",
            "auth", "--config", str(config_file), "--profile", "no_such_xyz",
        ],
        tmp_path,
    )
    assert result.returncode == 5
    for line in result.stderr.splitlines():
        if not line.strip():
            continue
        payload = _assert_json_record(line)
        assert payload["logger"] == "__main__", (
            f"unexpected logger name: {payload['logger']!r}"
        )


def test_json_logs_records_land_in_file(
    tmp_path: Path, config_file: Path
) -> None:
    """The file handler must also receive JSON records."""
    result = _run(
        [
            "--json-log-records",
            "auth", "--config", str(config_file), "--profile", "no_such_xyz",
        ],
        tmp_path,
    )
    assert result.returncode == 5

    app_log = tmp_path / "logs" / "app.log"
    assert app_log.is_file()
    for line in app_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        # Each line in the file is JSON because --json-log-records is global.
        _assert_json_record(line)


def test_json_logs_timestamp_format(
    tmp_path: Path, config_file: Path
) -> None:
    """The ``ts`` field must be ISO-8601 with timezone offset."""
    result = _run(
        [
            "--json-log-records",
            "auth", "--config", str(config_file), "--profile", "no_such_xyz",
        ],
        tmp_path,
    )
    assert result.returncode == 5
    for line in result.stderr.splitlines():
        if not line.strip():
            continue
        payload = _assert_json_record(line)
        ts = payload["ts"]
        assert "T" in ts
        # Must end with a timezone offset like +0000 or +0300.
        assert re.search(r"[+-]\d{4}$", ts), f"bad timezone offset: {ts!r}"


import re  # noqa: E402  -- placed after non-import for the helper above


def test_json_logs_no_human_format_leak(
    tmp_path: Path, config_file: Path
) -> None:
    """When --json-log-records is on, the console must NOT contain any of the
    human-format tokens (no ``|``-separated level names)."""
    result = _run(
        [
            "--json-log-records",
            "auth", "--config", str(config_file), "--profile", "no_such_xyz",
        ],
        tmp_path,
    )
    assert result.returncode == 5
    for line in result.stderr.splitlines():
        if not line.strip():
            continue
        # Human format embeds `` | INFO | ...`` so look for `` | ``.
        assert " | INFO " not in line, f"human-format leak: {line!r}"
        assert " | ERROR " not in line, f"human-format leak: {line!r}"
        assert " | WARNING " not in line, f"human-format leak: {line!r}"


def test_human_format_default(tmp_path: Path, config_file: Path) -> None:
    """Without --json-log-records, the console must use the human format
    (pipe-separated level), and that must NOT be valid JSON.
    """
    result = _run(
        ["auth", "--config", str(config_file), "--profile", "no_such_xyz"],
        tmp_path,
    )
    assert result.returncode == 5
    found_human = False
    for line in result.stderr.splitlines():
        if not line.strip():
            continue
        if " | ERROR " in line:
            found_human = True
            break
        # Every non-empty line must be either JSON or human format.
        try:
            json.loads(line)
        except json.JSONDecodeError:
            # Good — line is not JSON.
            pass
        else:
            pytest.fail(f"unexpected JSON record when --json-log-records is off: {line!r}")
    assert found_human, "no human-format ERROR line found on stderr"