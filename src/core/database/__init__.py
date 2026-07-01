"""Database module for database connection and query management.

This module contains all database-related functionality including:
- Database connection management
- Database credentials handling
- Database connection pooling
- Database query execution
"""

from .database import DatabaseManager, get_db_manager, init_db, close_db

__all__ = [
    "DatabaseManager",
    "get_db_manager",
    "init_db",
    "close_db",
]

