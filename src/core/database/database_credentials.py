"""Database path loading and validation for local SQLite."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Project root: src/core/database -> parents[3]
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DB_PATH = _PROJECT_ROOT / "state" / "manual_review_decisions.db"


class DatabaseCredentials:
    """Resolves the local SQLite database path."""

    def __init__(self, path: Optional[str | Path] = None):
        """Initialize path from argument, env, or project default."""
        load_dotenv()
        if path is not None:
            self.path = Path(path)
        else:
            env_path = os.getenv("SQLITE_DB_PATH") or os.getenv("MANUAL_REVIEW_DB_PATH")
            self.path = Path(env_path) if env_path else _DEFAULT_DB_PATH
        if not self.path.is_absolute():
            self.path = (_PROJECT_ROOT / self.path).resolve()


__all__ = ["DatabaseCredentials", "_DEFAULT_DB_PATH", "_PROJECT_ROOT"]
