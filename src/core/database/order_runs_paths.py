"""Filesystem path resolution for the order-runs database.

Mirrors :mod:`src.core.database.database_credentials` but keeps the order-runs
database on its own path so it can be deleted, vacuumed, or restored without
touching human-approved manual-review decisions.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# src/core/database -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ORDER_RUNS_DB = PROJECT_ROOT / "state" / "order_runs.db"
ORDER_RUNS_PATH_ENV = "ORDER_RUNS_DB_PATH"


def default_order_runs_db() -> Path:
    """Return the configured order-runs database path.

    Resolution order: ``ORDER_RUNS_DB_PATH`` environment variable, then the
    project default ``state/order_runs.db``. Relative paths resolve against the
    project root so subprocess workers agree with the parent process regardless
    of their working directory.
    """
    load_dotenv()
    configured = os.getenv(ORDER_RUNS_PATH_ENV)
    path = Path(configured) if configured else DEFAULT_ORDER_RUNS_DB
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


__all__ = [
    "PROJECT_ROOT",
    "DEFAULT_ORDER_RUNS_DB",
    "ORDER_RUNS_PATH_ENV",
    "default_order_runs_db",
]
