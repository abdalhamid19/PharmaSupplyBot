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
from .order_runs_migrations import MIGRATIONS
from .order_runs_tables import (
    CREATE_ITEMS,
    CREATE_PRODUCTS,
    CREATE_RUNS,
    CREATE_RUN_ITEMS,
    CREATE_SCHEMA_META,
    CREATE_STORES,
)
from .order_runs_version import SCHEMA_VERSION, SCHEMA_VERSION_KEY
from .order_runs_views import ALL_VIEWS

# Views referenced by name in ALL_DDL use ``if not exists`` so concurrent
# workers stay safe, but a stored view keeps its original definition forever.
# When a view definition changes between schema versions the migration below
# drops the stale object so bootstrap recreates it with the current SQL.
STALE_VIEWS_BY_VERSION = {
    1: ("v_run_summary",),
}

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
    "STALE_VIEWS_BY_VERSION",
    "MIGRATIONS",
    "CREATE_TABLES",
    "ALL_DDL",
    "UPSERT_SCHEMA_VERSION",
    "SELECT_SCHEMA_VERSION",
]
