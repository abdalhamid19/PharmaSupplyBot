"""Centralized logging configuration for the PharmaSupplyBot CLI.

This module is the single entry point for configuring Python's logging
package across the entire CLI. It is intentionally framework-agnostic
and exposes one helper: :func:`configure_logging`.

Design goals
------------
* Zero new dependencies (stdlib only).
* Per-run files written to ``logs/`` with automatic rotation.
* Predictable routing: WARNING+ to stderr, everything else to stdout
  unless the caller opts into ``--quiet``.
* Honors CLI flags: ``--log-level``, ``--quiet``, ``--json-logs``.
* Idempotent: calling :func:`configure_logging` twice is safe — the
  second call replaces handlers on the root logger only, so existing
  loggers (created via ``logging.getLogger(__name__)``) automatically
  inherit the new config.

Routing rules
-------------
========================  ==========================
Level                     Where it goes
========================  ==========================
DEBUG (--quiet OFF)       stdout + ``logs/app.log``
INFO  (--quiet OFF)       stdout + ``logs/app.log``
WARNING                   stderr + ``logs/app.log``
ERROR                     stderr + ``logs/app.log`` + ``logs/errors.log``
CRITICAL                  stderr + ``logs/app.log`` + ``logs/errors.log``
DEBUG/INFO (--quiet ON)   ``logs/app.log`` only (console suppressed)
========================  ==========================
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_LEVEL: int = logging.INFO
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S%z"
LOG_DIR: Path = Path("logs")
APP_LOG_FILE: str = "app.log"
ERROR_LOG_FILE: str = "errors.log"
ROTATION_WHEN: str = "midnight"
ROTATION_BACKUPS: int = 14  # أسبوعين من الملفات


@dataclass(frozen=True)
class LoggingConfig:
    """Immutable bundle of CLI-derived logging options."""

    level: str = "INFO"
    quiet: bool = False
    json_logs: bool = False
    log_dir: Path = LOG_DIR


# ─────────────────────────── Formatters ───────────────────────────


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object.

    Standard :class:`logging.LogRecord` attributes are mapped to a
    stable schema (``ts``, ``level``, ``logger``, ``message``,
    ``exception``). Anything passed via ``logger.info("...", extra={...})``
    is merged in, except internal fields prefixed with ``_``.
    """

    # الحقول القياسية التي لا نريد تكرارها من record.__dict__
    _RESERVED = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "asctime", "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, DATE_FORMAT),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # ضمّ الحقول المخصصة من extra={...}
        for key, value in record.__dict__.items():
            if key in self._RESERVED or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = record.stack_info
        return json.dumps(payload, ensure_ascii=False, default=str)


# ─────────────────────────── Public API ───────────────────────────


def configure_logging(config: LoggingConfig | None = None) -> None:
    """Initialize the root logger with handlers derived from ``config``.

    Safe to call multiple times — subsequent calls remove the previously
    attached handlers before adding fresh ones, so calling this twice
    in tests / REPL does not duplicate output.

    The handler set is:

    * one console handler (stderr), level filtered by ``quiet`` flag
    * one rotating app file (``logs/app.log``), captures DEBUG+
    * one rotating error file (``logs/errors.log``), captures ERROR+
    """
    cfg = config or LoggingConfig()
    root = logging.getLogger()
    root.setLevel(_resolve_level(cfg.level))

    # إزالة أي handlers سابقة — يمنع التكرار عند إعادة الاستدعاء
    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # pragma: no cover - defensive
            pass

    for handler in (
        _build_console_handler(cfg, root.level),
        _build_app_file_handler(cfg),
        _build_error_file_handler(cfg),
    ):
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger — thin wrapper for testability."""
    return logging.getLogger(name)


# ─────────────────────────── Internals ───────────────────────────


def _resolve_level(level: str) -> int:
    """Translate a string level (e.g. 'DEBUG') to its numeric value."""
    numeric = logging.getLevelName(level.upper())
    if not isinstance(numeric, int):
        raise ValueError(f"Unknown log level: {level!r}")
    return numeric


def _build_console_handler(cfg: LoggingConfig, root_level: int) -> logging.Handler:
    """Console handler on stderr; WARNING+ always visible, rest gated by --quiet.

    We deliberately do *not* pass ``stream=sys.stderr`` at construction
    time. With a captured argument, the handler holds a reference to
    that specific stream object forever; if a test runner (e.g. pytest)
    later swaps out ``sys.stderr`` for a capture object, the handler
    keeps writing to the *original* stream and the test sees nothing.
    Using the no-arg form means the handler resolves ``sys.stderr`` on
    every ``emit`` call, picking up whatever the runtime has in place.
    """
    handler = logging.StreamHandler()
    if cfg.quiet:
        handler.setLevel(logging.WARNING)
    else:
        handler.setLevel(root_level)
    handler.setFormatter(_select_formatter(cfg))
    return handler


def _build_app_file_handler(cfg: LoggingConfig) -> logging.Handler:
    """Rotating file handler for the general application log."""
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.log_dir / APP_LOG_FILE
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=path,
        when=ROTATION_WHEN,
        backupCount=ROTATION_BACKUPS,
        encoding="utf-8",
        utc=False,
    )
    handler.setLevel(logging.DEBUG)  # خزّن كل شيء في الملف
    handler.setFormatter(_select_formatter(cfg))
    return handler


def _build_error_file_handler(cfg: LoggingConfig) -> logging.Handler:
    """Separate file for ERROR+ records (easier alerting later)."""
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.log_dir / ERROR_LOG_FILE
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=path,
        when=ROTATION_WHEN,
        backupCount=ROTATION_BACKUPS,
        encoding="utf-8",
        utc=False,
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(_select_formatter(cfg))
    return handler


def _select_formatter(cfg: LoggingConfig) -> logging.Formatter:
    return JsonFormatter() if cfg.json_logs else logging.Formatter(
        fmt=LOG_FORMAT, datefmt=DATE_FORMAT,
    )


__all__ = [
    "LoggingConfig",
    "JsonFormatter",
    "configure_logging",
    "get_logger",
    "DEFAULT_LEVEL",
    "LOG_FORMAT",
    "DATE_FORMAT",
    "LOG_DIR",
    "APP_LOG_FILE",
    "ERROR_LOG_FILE",
    "ROTATION_WHEN",
    "ROTATION_BACKUPS",
]