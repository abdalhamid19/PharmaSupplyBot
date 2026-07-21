"""Tests for the unified logging integration with matching workflows.

These tests cover the deprecation wrappers added in the
setup_logging / configure_async_logging consolidation. They ensure
that:

* The matching-scoped logger (pharmasupplybot.matching) inherits from
  the root logger, so messages reach logs/app.log.
* setup_logging() is now a no-op for the root handler chain (does not
  call basicConfig).
* configure_async_logging() returns (logger, None) — no QueueListener.
* async_matching_logging() still works as a context manager.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from src.cli.logging_setup import LoggingConfig, configure_logging


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """Restore root logger after each test (matches test_logging_setup)."""
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


# ─────────────────────────── Deprecation wrappers ───────────────────────────


def test_setup_logging_does_not_destroy_handlers(tmp_path: Path) -> None:
    """setup_logging must NOT call basicConfig — it must preserve handlers."""
    configure_logging(LoggingConfig(log_dir=tmp_path, level="DEBUG"))
    root = logging.getLogger()
    handlers_before = sorted(
        (type(h).__name__, getattr(h, "baseFilename", str(h)))
        for h in root.handlers
    )

    from src.core.drug_matching.config.config_helpers import setup_logging
    setup_logging("DEBUG")

    handlers_after = sorted(
        (type(h).__name__, getattr(h, "baseFilename", str(h)))
        for h in root.handlers
    )
    assert handlers_before == handlers_after, (
        "setup_logging must not modify the root handler chain"
    )


def test_setup_logging_sets_matching_logger_level() -> None:
    """setup_logging only adjusts the matching logger level."""
    from src.core.drug_matching.config.config_helpers import setup_logging
    setup_logging("DEBUG")
    assert logging.getLogger("pharmasupplybot.matching").level == logging.DEBUG
    setup_logging("WARNING")
    assert logging.getLogger("pharmasupplybot.matching").level == logging.WARNING


def test_setup_logging_handles_unknown_level_gracefully() -> None:
    """Unknown level string falls back to INFO (matches old behaviour)."""
    from src.core.drug_matching.config.config_helpers import setup_logging
    setup_logging("BOGUS_LEVEL")
    assert logging.getLogger("pharmasupplybot.matching").level == logging.INFO


def test_configure_async_logging_returns_none_listener() -> None:
    """The new configure_async_logging returns (logger, None)."""
    from src.core.matching.matching_trace import configure_async_logging
    logger, listener = configure_async_logging("INFO")
    assert listener is None
    assert logger.name == "pharmasupplybot.matching"


def test_configure_async_logging_clears_handlers_and_enables_propagate() -> None:
    """The matching logger must propagate to root after configure_async_logging."""
    matching = logging.getLogger("pharmasupplybot.matching")
    # Pre-condition: pre-populate a stale handler that needs to be cleared
    matching.addHandler(logging.NullHandler())
    matching.propagate = False

    from src.core.matching.matching_trace import configure_async_logging
    logger, _ = configure_async_logging("INFO")

    assert logger.handlers == [], "configure_async_logging must clear handlers"
    assert logger.propagate is True, "must propagate to root for app.log capture"


def test_async_matching_logging_context_manager_yields_logger() -> None:
    """async_matching_logging is a working context manager that yields a logger."""
    from src.core.matching.matching_trace import async_matching_logging
    with async_matching_logging("INFO") as logger:
        assert logger.name == "pharmasupplybot.matching"


def test_async_matching_logging_does_not_start_a_thread() -> None:
    """No QueueListener means no background thread is created."""
    import threading
    threads_before = {t.ident for t in threading.enumerate()}

    from src.core.matching.matching_trace import async_matching_logging
    with async_matching_logging("INFO"):
        pass

    threads_after = {t.ident for t in threading.enumerate()}
    assert threads_before == threads_after, (
        "async_matching_logging must not spawn a QueueListener thread"
    )


# ─────────────────────────── Unified integration ───────────────────────────


def test_matching_logger_writes_to_app_log(tmp_path: Path) -> None:
    """Records from pharmasupplybot.matching must land in logs/app.log."""
    configure_logging(LoggingConfig(log_dir=tmp_path, level="DEBUG"))
    matching = logging.getLogger("pharmasupplybot.matching")
    matching.info("match started", extra={"count": 5})
    matching.error("match failed", extra={"item": "panadol"})

    text = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "match started" in text
    assert "match failed" in text
    # Extra fields are present in the human formatter as well? No — they are
    # added as attributes but the formatter filters them. We just check
    # the message text is there.


def test_matching_logger_writes_to_errors_log(tmp_path: Path) -> None:
    """ERROR+ from the matching logger must also land in logs/errors.log."""
    configure_logging(LoggingConfig(log_dir=tmp_path, level="DEBUG"))
    matching = logging.getLogger("pharmasupplybot.matching")
    matching.info("below_threshold")
    matching.error("above_threshold")

    err_text = (tmp_path / "errors.log").read_text(encoding="utf-8")
    assert "below_threshold" not in err_text
    assert "above_threshold" in err_text


def test_matching_logger_inherits_quiet_mode(tmp_path: Path, capsys) -> None:
    """--quiet suppresses matching logger INFO on stderr."""
    configure_logging(
        LoggingConfig(log_dir=tmp_path, level="DEBUG", quiet=True)
    )
    matching = logging.getLogger("pharmasupplybot.matching")
    matching.info("info_match")
    matching.warning("warn_match")

    captured = capsys.readouterr()
    assert "info_match" not in captured.err
    assert "warn_match" in captured.err


def test_matching_logger_supports_json_output(tmp_path: Path, capsys) -> None:
    """--json-logs formats matching logger output as JSON."""
    import json
    configure_logging(
        LoggingConfig(log_dir=tmp_path, level="INFO", json_logs=True)
    )
    matching = logging.getLogger("pharmasupplybot.matching")
    matching.info("event", extra={"profile": "wardany"})

    line = capsys.readouterr().err.strip().splitlines()[0]
    payload = json.loads(line)
    assert payload["logger"] == "pharmasupplybot.matching"
    assert payload["message"] == "event"
    assert payload["profile"] == "wardany"


def test_root_logger_setup_then_setup_logging_is_safe(tmp_path: Path) -> None:
    """The exact bug this commit fixes: configure_logging then setup_logging
    should leave the file handlers intact."""
    configure_logging(LoggingConfig(log_dir=tmp_path, level="DEBUG"))

    from src.core.drug_matching.config.config_helpers import setup_logging
    setup_logging("INFO")  # would have destroyed app.log handler in old code

    # File still exists and accepts writes
    log = logging.getLogger("test.after_setup_logging")
    log.info("survived")
    text = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "survived" in text