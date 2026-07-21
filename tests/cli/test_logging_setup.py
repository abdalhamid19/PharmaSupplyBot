"""Tests for the centralized logging configuration."""

from __future__ import annotations

import json
import logging
import logging.handlers
from pathlib import Path

import pytest

from src.cli.logging_setup import (
    APP_LOG_FILE,
    DATE_FORMAT,
    ERROR_LOG_FILE,
    JsonFormatter,
    LoggingConfig,
    LOG_DIR,
    LOG_FORMAT,
    configure_logging,
    get_logger,
)


@pytest.fixture
def log_dir(tmp_path: Path) -> Path:
    """Per-test log directory; configure_logging will create it."""
    return tmp_path


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """Restore the root logger to a clean state after each test.

    configure_logging is supposed to be idempotent, but if a test
    installs extra handlers or sets a non-default level, the next
    test should not see those side effects.
    """
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    yield
    for handler in list(root.handlers):
        try:
            handler.close()
        except Exception:
            pass
        root.removeHandler(handler)
    for handler in saved_handlers:
        root.addHandler(handler)
    root.setLevel(saved_level)


# ─────────────────────────── configure_logging ───────────────────────────


def test_configure_logging_creates_log_dir(log_dir: Path) -> None:
    # tmp_path is auto-created by pytest; we just want to verify the
    # configure_logging call puts the expected files inside it.
    configure_logging(LoggingConfig(log_dir=log_dir))
    assert log_dir.is_dir()
    assert (log_dir / APP_LOG_FILE).exists()
    assert (log_dir / ERROR_LOG_FILE).exists()


def test_configure_logging_is_idempotent(log_dir: Path) -> None:
    configure_logging(LoggingConfig(log_dir=log_dir))
    first = len(logging.getLogger().handlers)
    configure_logging(LoggingConfig(log_dir=log_dir, level="DEBUG"))
    second = len(logging.getLogger().handlers)
    assert first == second, "handler count must not grow between calls"


def test_configure_logging_honors_level(log_dir: Path) -> None:
    configure_logging(LoggingConfig(level="WARNING", log_dir=log_dir))
    logger = get_logger("test.level")
    logger.info("not emitted")
    logger.warning("emitted")
    text = (log_dir / APP_LOG_FILE).read_text(encoding="utf-8")
    assert "not emitted" not in text
    assert "emitted" in text


def test_quiet_silences_console_but_still_writes_files(
    log_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging(LoggingConfig(level="DEBUG", quiet=True, log_dir=log_dir))
    logger = get_logger("test.quiet")
    logger.info("below_threshold")
    logger.warning("above_threshold")
    captured = capsys.readouterr()
    # Console: only WARNING+ shows up
    assert "below_threshold" not in captured.err
    assert "above_threshold" in captured.err
    # File: everything below WARNING is still recorded
    text = (log_dir / APP_LOG_FILE).read_text(encoding="utf-8")
    assert "below_threshold" in text
    assert "above_threshold" in text


def test_json_logs_emits_valid_json(
    log_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging(LoggingConfig(level="INFO", json_logs=True, log_dir=log_dir))
    logger = get_logger("test.json")
    logger.info("hello world", extra={"profile": "wardany", "count": 7})
    captured = capsys.readouterr()
    # First line of stderr must be a parseable JSON object
    line = captured.err.splitlines()[0]
    payload = json.loads(line)
    assert payload["message"] == "hello world"
    assert payload["logger"] == "test.json"
    assert payload["level"] == "INFO"
    assert payload["profile"] == "wardany"
    assert payload["count"] == 7


def test_error_file_only_records_errors_and_above(log_dir: Path) -> None:
    configure_logging(LoggingConfig(level="DEBUG", log_dir=log_dir))
    logger = get_logger("test.errors")
    logger.debug("debug_entry")
    logger.info("info_entry")
    logger.warning("warning_entry")
    logger.error("error_entry")
    logger.critical("critical_entry")
    err_text = (log_dir / ERROR_LOG_FILE).read_text(encoding="utf-8")
    assert "debug_entry" not in err_text
    assert "info_entry" not in err_text
    assert "warning_entry" not in err_text
    assert "error_entry" in err_text
    assert "critical_entry" in err_text


def test_app_file_records_everything(log_dir: Path) -> None:
    configure_logging(LoggingConfig(level="DEBUG", log_dir=log_dir))
    logger = get_logger("test.app")
    logger.debug("debug_entry")
    logger.info("info_entry")
    logger.error("error_entry")
    text = (log_dir / APP_LOG_FILE).read_text(encoding="utf-8")
    assert "debug_entry" in text
    assert "info_entry" in text
    assert "error_entry" in text


# ─────────────────────────── JsonFormatter ───────────────────────────


def test_json_formatter_uses_iso_timestamp() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="x", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hi", args=(), exc_info=None,
    )
    out = formatter.format(record)
    payload = json.loads(out)
    # DATE_FORMAT is "%Y-%m-%dT%H:%M:%S%z" — 2025-01-01T12:00:00+0000 style
    assert "T" in payload["ts"]
    assert "+" in payload["ts"] or "-" in payload["ts"]


def test_json_formatter_handles_exception() -> None:
    formatter = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="x", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="failed", args=(), exc_info=sys.exc_info(),
        )
    out = formatter.format(record)
    payload = json.loads(out)
    assert "exception" in payload
    assert "ValueError: boom" in payload["exception"]


def test_json_formatter_includes_extra_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="x", level=logging.INFO, pathname=__file__, lineno=1,
        msg="event", args=(), exc_info=None,
    )
    record.profile = "wardany"  # type: ignore[attr-defined]
    record._internal = "should_be_skipped"  # type: ignore[attr-defined]
    out = formatter.format(record)
    payload = json.loads(out)
    assert payload["profile"] == "wardany"
    assert "_internal" not in payload


def test_get_logger_returns_logger_with_correct_name() -> None:
    logger = get_logger("test.get")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.get"


def test_unknown_level_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown log level"):
        configure_logging(LoggingConfig(level="NOT_A_LEVEL"))


# ─────────────────────────── Rotation metadata ───────────────────────────


def test_handlers_are_rotating_file_handlers(log_dir: Path) -> None:
    configure_logging(LoggingConfig(log_dir=log_dir))
    handlers = [
        h for h in logging.getLogger().handlers
        if isinstance(h, logging.handlers.TimedRotatingFileHandler)
    ]
    assert len(handlers) == 2  # app + errors
    filenames = {Path(h.baseFilename).name for h in handlers}
    assert filenames == {APP_LOG_FILE, ERROR_LOG_FILE}


def test_default_values_constants() -> None:
    """Lock in the public defaults so accidental changes are caught."""
    assert LOG_DIR == Path("logs")
    assert APP_LOG_FILE == "app.log"
    assert ERROR_LOG_FILE == "errors.log"
    assert DATE_FORMAT == "%Y-%m-%dT%H:%M:%S%z"
    assert "asctime" in LOG_FORMAT
    assert "levelname" in LOG_FORMAT
    assert "name" in LOG_FORMAT
    assert "message" in LOG_FORMAT