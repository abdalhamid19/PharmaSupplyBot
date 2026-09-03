"""Database module for local SQLite connection and query management.

This module contains all database-related functionality including:
- Database connection management
- Database path / credentials handling
- SQLite connection pooling
- Database query execution
- Order-run analytics storage (separate database file)
"""

from .database import DatabaseManager, get_db_manager, init_db, close_db
from .order_runs_paths import DEFAULT_ORDER_RUNS_DB, default_order_runs_db
from .order_runs_store import OrderRunsStore, order_runs_store

__all__ = [
    "DatabaseManager",
    "get_db_manager",
    "init_db",
    "close_db",
    "DEFAULT_ORDER_RUNS_DB",
    "default_order_runs_db",
    "OrderRunsStore",
    "order_runs_store",
]

