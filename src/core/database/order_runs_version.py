"""Schema version constants for the order-runs database.

Kept in its own module so :mod:`order_runs_migrations` can import the
version without depending on the rest of the schema bootstrap. Moving the
constant here also breaks the circular import between
:mod:`order_runs_schema` and :mod:`order_runs_migrations` that would
otherwise prevent bootstrap from completing.
"""

from __future__ import annotations

SCHEMA_VERSION = 5
SCHEMA_VERSION_KEY = "schema_version"

__all__ = ["SCHEMA_VERSION", "SCHEMA_VERSION_KEY"]
