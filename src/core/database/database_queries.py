"""Database query execution methods for SQLite."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)


class DatabaseQueries:
    """Handles SQLite query execution."""

    def __init__(self, pool):
        """Initialize query executor with a connection pool."""
        self.pool = pool

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a SELECT (or PRAGMA) query and return rows."""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            results = cur.fetchall()
            cur.close()
            return results

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE and return affected rows."""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            affected = cur.rowcount
            conn.commit()
            cur.close()
            return affected

    def test_connection(self) -> bool:
        """Test the SQLite connection."""
        try:
            with self.pool.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT sqlite_version();")
                result = cur.fetchone()
                logger.info("SQLite test successful: version %s", result[0])
                cur.close()
                return True
        except sqlite3.Error as e:
            logger.error("SQLite test failed: %s", e)
            return False


__all__ = ["DatabaseQueries"]
