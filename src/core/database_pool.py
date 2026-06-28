"""Database connection pool management."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional
from psycopg2 import pool, Error
import logging

logger = logging.getLogger(__name__)


class DatabasePool:
    """Manages connection pool to CockroachDB Cloud."""

    def __init__(self, credentials):
        """Initialize connection pool with credentials."""
        self.credentials = credentials
        self.connection_pool: Optional[pool.SimpleConnectionPool] = None

    def connect(self) -> None:
        """Initialize connection pool to CockroachDB Cloud."""
        if not self.credentials.password:
            raise RuntimeError("DB_PASSWORD is not configured. Set DB_PASSWORD for CockroachDB.")
        self._create_connection_pool()
        logger.info(f"Connected to CockroachDB: {self.credentials.host}:{self.credentials.port}")

    def _create_connection_pool(self):
        """Create the connection pool."""
        try:
            self.connection_pool = pool.SimpleConnectionPool(
                1, 5,
                host=self.credentials.host,
                port=self.credentials.port,
                database=self.credentials.database,
                user=self.credentials.user,
                password=self.credentials.password,
                sslmode=self.credentials.sslmode
            )
        except Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def close(self) -> None:
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connections closed")

    @contextmanager
    def get_connection(self) -> Generator:
        """Get a connection from the pool (context manager)."""
        if not self.connection_pool:
            raise RuntimeError("Database not connected. Call connect() first.")
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            self.connection_pool.putconn(conn)


__all__ = ["DatabasePool"]
