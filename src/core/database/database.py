"""
CockroachDB Cloud Connection Manager
Handles connections to the shared cloud database for manual review data synchronization.
"""

from __future__ import annotations

from typing import Optional

from .database_credentials import DatabaseCredentials
from .database_pool import DatabasePool
from .database_queries import DatabaseQueries


class DatabaseManager(DatabaseQueries):
    """Manages connections to CockroachDB Cloud."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        sslmode: Optional[str] = None,
    ):
        """Initialize database manager with connection parameters."""
        credentials = DatabaseCredentials(host, port, database, user, password, sslmode)
        self.credentials = credentials
        self._pool = DatabasePool(credentials)
        super().__init__(self._pool)

    def connect(self) -> None:
        """Initialize connection pool to CockroachDB Cloud."""
        self._pool.connect()

    def close(self) -> None:
        """Close all connections in the pool."""
        self._pool.close()

    @property
    def get_connection(self):
        """Get connection from pool (alias for backward compatibility)."""
        return self._pool.get_connection


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.connect()
    return _db_manager


def init_db(password: Optional[str] = None) -> DatabaseManager:
    """Initialize database connection (call once on app startup)."""
    global _db_manager
    _db_manager = DatabaseManager(password=password)
    _db_manager.connect()
    return _db_manager


def close_db() -> None:
    """Close database connections (call on app shutdown)."""
    global _db_manager
    if _db_manager:
        _db_manager.close()


__all__ = [
    "DatabaseManager",
    "get_db_manager",
    "init_db",
    "close_db",
]
