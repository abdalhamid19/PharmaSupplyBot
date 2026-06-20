"""
CockroachDB Cloud Connection Manager
Handles connections to the shared cloud database for manual review data synchronization.
"""

import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool, Error
from contextlib import contextmanager
from typing import Optional, Generator, Any
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages connections to CockroachDB Cloud."""
    
    # Default connection parameters
    DEFAULT_HOST = "mahrousdb-27867.j77.aws-eu-central-1.cockroachlabs.cloud"
    DEFAULT_PORT = 26257
    DEFAULT_DATABASE = "defaultdb"
    DEFAULT_USER = "abdalhamid"
    DEFAULT_SSLMODE = "require"
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        sslmode: Optional[str] = None,
    ):
        """
        Initialize database manager with connection parameters.
        
        Defaults to environment variables or hardcoded cloud defaults.
        """
        load_dotenv()
        self.host = host or os.getenv("DB_HOST", self.DEFAULT_HOST)
        self.port = port or int(os.getenv("DB_PORT", self.DEFAULT_PORT))
        self.database = database or os.getenv("DB_NAME", self.DEFAULT_DATABASE)
        self.user = user or os.getenv("DB_USER", self.DEFAULT_USER)
        self.password = password if password is not None else os.getenv("DB_PASSWORD", "")
        self.sslmode = sslmode or os.getenv("DB_SSLMODE", self.DEFAULT_SSLMODE)
        
        self.connection_pool: Optional[pool.SimpleConnectionPool] = None
    
    def connect(self) -> None:
        """Initialize connection pool to CockroachDB Cloud."""
        if not self.password:
            raise RuntimeError(
                "DB_PASSWORD is not configured. Set DB_PASSWORD for CockroachDB."
            )
        try:
            self.connection_pool = pool.SimpleConnectionPool(
                1,
                5,  # Min 1, Max 5 connections
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                sslmode=self.sslmode,
            )
            logger.info(f"Connected to CockroachDB: {self.host}:{self.port}")
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
        """
        Get a connection from the pool (context manager).
        
        Usage:
            with db_manager.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM table")
        """
        if not self.connection_pool:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            self.connection_pool.putconn(conn)
    
    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a SELECT query and return results."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            results = cur.fetchall()
            cur.close()
            return results
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            affected = cur.rowcount
            conn.commit()
            cur.close()
            return affected
    
    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT version();")
                result = cur.fetchone()
                logger.info(f"Database test successful: {result[0][:50]}...")
                cur.close()
                return True
        except Error as e:
            logger.error(f"Database test failed: {e}")
            return False


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
