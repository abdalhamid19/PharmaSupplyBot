"""Schema introspection for the order-runs database.

Used by tests and by ``db-import`` to verify a database file has the expected
shape before writing to it. Exposed as a mixin so the store facade stays thin.
"""

from __future__ import annotations

SELECT_TABLE_NAMES = "select name from sqlite_master where type = 'table'"
SELECT_VIEW_NAMES = "select name from sqlite_master where type = 'view'"
PRAGMA_FOREIGN_KEYS = "PRAGMA foreign_keys"


class OrderRunsIntrospectMixin:
    """Schema inspection helpers for the order-runs database."""

    def table_names(self) -> set[str]:
        """Return every table name present in the database."""
        return self._object_names(SELECT_TABLE_NAMES)

    def view_names(self) -> set[str]:
        """Return every view name present in the database."""
        return self._object_names(SELECT_VIEW_NAMES)

    def column_names(self, table: str) -> list[str]:
        """Return every column name for a table in declaration order."""
        return [str(row[1]) for row in self._table_info(table)]

    def primary_key_columns(self, table: str) -> list[str]:
        """Return primary-key column names in key order.

        ``PRAGMA table_info`` rows are ``(cid, name, type, notnull, dflt, pk)``
        where ``pk`` is the 1-based position inside the key, or 0.
        """
        keyed = [
            (int(row[5]), str(row[1])) for row in self._table_info(table) if int(row[5])
        ]
        return [name for _, name in sorted(keyed)]

    def foreign_keys_enabled(self) -> bool:
        """Return whether the active connection enforces foreign keys."""
        rows = self.db.execute_query(PRAGMA_FOREIGN_KEYS)
        return bool(rows and int(rows[0][0]) == 1)

    def _object_names(self, query: str) -> set[str]:
        """Return sqlite_master object names for one object-type query."""
        return {str(row[0]) for row in self.db.execute_query(query)}

    def _table_info(self, table: str) -> list:
        """Return raw ``PRAGMA table_info`` rows for one table."""
        return self.db.execute_query(f"PRAGMA table_info({_safe_identifier(table)})")


def _safe_identifier(name: str) -> str:
    """Reject non-identifier table names; PRAGMA cannot use bound parameters."""
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe SQLite identifier: {name!r}")
    return name


__all__ = [
    "SELECT_TABLE_NAMES",
    "SELECT_VIEW_NAMES",
    "PRAGMA_FOREIGN_KEYS",
    "OrderRunsIntrospectMixin",
]
