"""Database module for local SQLite connection and query management.

This module contains all database-related functionality including:
- Database connection management
- Database path / credentials handling
- SQLite connection pooling
- Database query execution
"""

from .database import DatabaseManager, get_db_manager, init_db, close_db

__all__ = [
    "DatabaseManager",
    "get_db_manager",
    "init_db",
    "close_db",
]

