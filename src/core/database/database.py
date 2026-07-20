"""
SQLite connection manager for manual-review decisions.

Local file-based storage replaces the previous CockroachDB Cloud backend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .database_credentials import DatabaseCredentials, _DEFAULT_DB_PATH
from .database_pool import DatabasePool
from .database_queries import DatabaseQueries


class DatabaseManager(DatabaseQueries):
    """Manages connections to the local SQLite database."""

    def __init__(self, path: Optional[str | Path] = None):
        """Initialize database manager for a SQLite file path."""
        credentials = DatabaseCredentials(path)
        self.credentials = credentials
        self.path = credentials.path
        self._pool = DatabasePool(credentials)
        super().__init__(self._pool)

    def connect(self) -> None:
        """Initialize access to the SQLite database file."""
        self._pool.connect()

    def close(self) -> None:
        """Close database access."""
        self._pool.close()

    @property
    def get_connection(self):
        """Get connection from pool (alias for backward compatibility)."""
        return self._pool.get_connection


# Cache managers by resolved path so schema init is shared per file.
_db_managers: dict[str, DatabaseManager] = {}


def get_db_manager(path: Optional[str | Path] = None) -> DatabaseManager:
    """Get or create a database manager for the given (or default) path."""
    key = str(Path(path).resolve()) if path is not None else str(_DEFAULT_DB_PATH.resolve())
    manager = _db_managers.get(key)
    if manager is None:
        manager = DatabaseManager(path)
        manager.connect()
        _db_managers[key] = manager
    return manager


def init_db(path: Optional[str | Path] = None, password: Optional[str] = None) -> DatabaseManager:
    """Initialize database connection (call once on app startup).

    `password` is accepted for backward compatibility with the CockroachDB API
    and is ignored for SQLite.
    """
    del password  # unused; kept for call-site compatibility
    key = str(Path(path).resolve()) if path is not None else str(_DEFAULT_DB_PATH.resolve())
    manager = DatabaseManager(path)
    manager.connect()
    _db_managers[key] = manager
    return manager


def close_db() -> None:
    """Close all cached database managers."""
    for manager in list(_db_managers.values()):
        manager.close()
    _db_managers.clear()


__all__ = [
    "DatabaseManager",
    "get_db_manager",
    "init_db",
    "close_db",
]
