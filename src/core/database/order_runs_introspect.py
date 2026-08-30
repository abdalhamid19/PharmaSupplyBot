"""Schema introspection helpers for the order-runs database.

Used by tests and by the ``db-import`` command to verify a database file has
the expected shape before writing to it.
"""

from __future__ import annotations

SELECT_TABLE_NAMES = "select name from sqlite_master where type = 'table'"
SELECT_VIEW_NAMES = "select name from sqlite_master where type = 'view'"
PRAGMA_FOREIGN_KEYS = "PRAGMA foreign_keys"


def object_names(db, query: str) -> set[str]:
    """Return sqlite_master object names for one object-type query."""
    return {str(row[0]) for row in db.execute_query(query)}


def primary_key_columns(db, table: str) -> list[str]:
    """Return primary-key column names for a table in key order.

    ``PRAGMA table_info`` columns are ``(cid, name, type, notnull, dflt, pk)``
    where ``pk`` is the 1-based position inside the primary key, or 0.
    """
    rows = db.execute_query(f"PRAGMA table_info({_safe_identifier(table)})")
    keyed = [(int(row[5]), str(row[1])) for row in rows if int(row[5]) > 0]
    return [name for _, name in sorted(keyed)]


def column_names(db, table: str) -> list[str]:
    """Return every column name for a table in declaration order."""
    rows = db.execute_query(f"PRAGMA table_info({_safe_identifier(table)})")
    return [str(row[1]) for row in rows]


def foreign_keys_enabled(db) -> bool:
    """Return whether the active connection enforces foreign keys."""
    rows = db.execute_query(PRAGMA_FOREIGN_KEYS)
    return bool(rows and int(rows[0][0]) == 1)


def _safe_identifier(name: str) -> str:
    """Reject non-identifier table names; PRAGMA cannot use bound parameters."""
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe SQLite identifier: {name!r}")
    return name


__all__ = [
    "SELECT_TABLE_NAMES",
    "SELECT_VIEW_NAMES",
    "object_names",
    "primary_key_columns",
    "column_names",
    "foreign_keys_enabled",
]
