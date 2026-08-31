"""Schema definition and bootstrap order for the order-runs database.

The schema is deliberately split across three modules (dimension tables, fact
tables, views) so each stays small enough to read in one pass. This module owns
only the version number and the execution order.
"""

from __future__ import annotations

from .order_runs_facts import (
    CREATE_INDEXES,
    CREATE_RUN_CANDIDATES,
    CREATE_RUN_ITEM_STORES,
)
from .order_runs_tables import (
    CREATE_ITEMS,
    CREATE_PRODUCTS,
    CREATE_RUNS,
    CREATE_RUN_ITEMS,
    CREATE_SCHEMA_META,
    CREATE_STORES,
)
from .order_runs_views import ALL_VIEWS

SCHEMA_VERSION = 1
SCHEMA_VERSION_KEY = "schema_version"

# Order matters: dimensions before facts so foreign keys resolve, indexes and
# views last so they can reference every table.
CREATE_TABLES = (
    CREATE_SCHEMA_META,
    CREATE_RUNS,
    CREATE_ITEMS,
    CREATE_STORES,
    CREATE_PRODUCTS,
    CREATE_RUN_ITEMS,
    CREATE_RUN_ITEM_STORES,
    CREATE_RUN_CANDIDATES,
)

ALL_DDL = (*CREATE_TABLES, *CREATE_INDEXES, *ALL_VIEWS)

UPSERT_SCHEMA_VERSION = """
insert into schema_meta (key, value) values (?, ?)
on conflict(key) do update set value = excluded.value
"""

SELECT_SCHEMA_VERSION = "select value from schema_meta where key = ?"

__all__ = [
    "SCHEMA_VERSION",
    "SCHEMA_VERSION_KEY",
    "CREATE_TABLES",
    "ALL_DDL",
    "UPSERT_SCHEMA_VERSION",
    "SELECT_SCHEMA_VERSION",
]
