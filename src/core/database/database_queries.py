"""Database query execution methods."""

from __future__ import annotations

from typing import Optional
from psycopg2 import Error
import logging

logger = logging.getLogger(__name__)


class DatabaseQueries:
    """Handles database query execution."""

    def __init__(self, pool):
        """Initialize query executor with connection pool."""
        self.pool = pool

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a SELECT query and return results."""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            results = cur.fetchall()
            cur.close()
            return results

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            affected = cur.rowcount
            conn.commit()
            cur.close()
            return affected

    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            with self.pool.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT version();")
                result = cur.fetchone()
                logger.info(f"Database test successful: {result[0][:50]}...")
                cur.close()
                return True
        except Error as e:
            logger.error(f"Database test failed: {e}")
            return False


__all__ = ["DatabaseQueries"]
