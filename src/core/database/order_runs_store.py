"""SQLite store facade for order-run analytics tables.

Wraps the shared :class:`~src.core.database.database.DatabaseManager` with a
separate database file so run history never shares locking, vacuuming, or
durability settings with the manual-review decisions database.
"""

from __future__ import annotations

from pathlib import Path

from .database import get_db_manager
from .order_runs_introspect import OrderRunsIntrospectMixin
from .order_runs_paths import default_order_runs_db
from .order_runs_schema import (
    ALL_DDL,
    SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    SELECT_SCHEMA_VERSION,
    UPSERT_SCHEMA_VERSION,
)
from .order_runs_writer import OrderRunsWriterMixin


class OrderRunsStore(OrderRunsIntrospectMixin, OrderRunsWriterMixin):
    """Read/write facade for the order-runs database."""

    _bootstrapped_paths: set[str] = set()

    def __init__(self, path: str | Path | None = None, database_manager=None):
        """Open (or reuse) the order-runs database and ensure its schema."""
        if database_manager is not None:
            self.db = database_manager
            self.path = getattr(database_manager, "path", path)
        else:
            db_path = Path(path) if path is not None else default_order_runs_db()
            self.db = get_db_manager(db_path)
            self.path = self.db.path
        self._bootstrap_once()

    def schema_version(self) -> int:
        """Return the recorded schema version, or 0 when unrecorded."""
        rows = self.db.execute_query(SELECT_SCHEMA_VERSION, (SCHEMA_VERSION_KEY,))
        return int(rows[0][0]) if rows else 0

    def _bootstrap_once(self) -> None:
        """Create the schema once per database file in this process.

        Keyed by path, not connection: spawned workers start with an empty set,
        so all DDL stays ``IF NOT EXISTS``.
        """
        key = str(Path(self.path).resolve()) if self.path else str(id(self.db))
        if key in self._bootstrapped_paths:
            return
        self._create_schema()
        self._bootstrapped_paths.add(key)

    def _create_schema(self) -> None:
        """Execute the full DDL and record the schema version atomically."""
        with self.db.get_connection() as conn:
            for statement in ALL_DDL:
                conn.execute(statement)
            conn.execute(
                UPSERT_SCHEMA_VERSION, (SCHEMA_VERSION_KEY, str(SCHEMA_VERSION))
            )
            conn.commit()


def order_runs_store(path: str | Path | None = None) -> OrderRunsStore:
    """Return a store for the configured (or given) order-runs database path."""
    return OrderRunsStore(path)


__all__ = ["OrderRunsStore", "order_runs_store"]
