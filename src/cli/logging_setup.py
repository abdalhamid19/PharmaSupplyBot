"""Centralized logging configuration for the PharmaSupplyBot CLI.

Stage-1 skeleton: this module exposes just enough surface area for
``run.py`` to wire up the logging system before a real command runs.
The full implementation (file rotation, JSON output, --quiet support)
will land in Stage 2 of the logging_system rollout — see
``docs/logging_system.md`` for the design.

Stage-1 contract:

* :func:`configure_logging` is safe to call multiple times.
* :func:`get_logger` is the canonical accessor that every module in
  the project should use (``logging.getLogger(__name__)`` works too,
  but going through this helper keeps tests easier to monkey-patch).
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_LEVEL: int = logging.INFO
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S%z"
LOG_DIR: Path = Path("logs")


@dataclass(frozen=True)
class LoggingConfig:
    """Immutable bundle of CLI-derived logging options."""

    level: str = "INFO"
    quiet: bool = False
    json_logs: bool = False
    log_dir: Path = LOG_DIR


def configure_logging(config: LoggingConfig | None = None) -> None:
    """Initialize the root logger.

    Stage-1 behaviour: a single console handler is attached (stderr for
    WARNING+, stdout-equivalent for the rest). File handlers will be
    added in Stage 2.
    """
    cfg = config or LoggingConfig()
    root = logging.getLogger()
    root.setLevel(_resolve_level(cfg.level))

    # Remove any handlers we previously attached (idempotent re-init).
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler(stream=sys.stderr)
    if cfg.quiet:
        console.setLevel(logging.WARNING)
    else:
        console.setLevel(root.level)
    console.setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(console)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


def _resolve_level(level: str) -> int:
    """Translate a string level (e.g. 'DEBUG') to its numeric value."""
    numeric = logging.getLevelName(level.upper())
    if not isinstance(numeric, int):
        raise ValueError(f"Unknown log level: {level!r}")
    return numeric


__all__ = [
    "LoggingConfig",
    "configure_logging",
    "get_logger",
    "DEFAULT_LEVEL",
    "LOG_FORMAT",
    "DATE_FORMAT",
    "LOG_DIR",
]