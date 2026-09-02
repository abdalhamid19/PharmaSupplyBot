"""Table DDL for the order-runs analytics database.

Every statement is ``IF NOT EXISTS`` so concurrent item workers can each run
the full schema bootstrap without coordinating.
"""

from __future__ import annotations

CREATE_SCHEMA_META = """
create table if not exists schema_meta (
    key   TEXT primary key,
    value TEXT not null
)
"""

CREATE_RUNS = """
create table if not exists runs (
    run_key          TEXT primary key,
    run_id           TEXT not null,
    profile_key      TEXT not null,
    command          TEXT not null default 'order',
    started_at       TEXT not null,
    finished_at      TEXT,
    mode             TEXT not null default '',
    execution_mode   TEXT not null default '',
    warehouse_mode   TEXT not null default '',
    min_discount_pct REAL,
    matching_risk    TEXT not null default '',
    excel_source     TEXT not null default '',
    item_workers     INTEGER not null default 1,
    artifact_dir     TEXT not null default '',
    total_items      INTEGER not null default 0,
    schema_version   INTEGER not null default 1
)
"""

CREATE_ITEMS = """
create table if not exists items (
    item_key      TEXT primary key,
    item_code     TEXT not null default '',
    item_name     TEXT not null default '',
    first_seen_at TEXT not null,
    last_seen_at  TEXT not null
)
"""

CREATE_STORES = """
create table if not exists stores (
    store_key     TEXT primary key,
    store_name    TEXT not null default '',
    first_seen_at TEXT not null,
    last_seen_at  TEXT not null
)
"""

CREATE_PRODUCTS = """
create table if not exists products (
    store_product_id TEXT primary key,
    product_id       TEXT not null default '',
    name_ar          TEXT not null default '',
    name_en          TEXT not null default '',
    is_synthetic     INTEGER not null default 0,
    first_seen_at    TEXT not null,
    last_seen_at     TEXT not null
)
"""

CREATE_RUN_ITEMS = """
create table if not exists run_items (
    run_key                 TEXT not null references runs(run_key) on delete cascade,
    item_key                TEXT not null references items(item_key),
    source_kind             TEXT not null default '',
    source_label            TEXT not null default '',
    requested_qty           INTEGER not null default 0,
    ordered_qty             INTEGER not null default 0,
    status                  TEXT not null default '',
    reason                  TEXT not null default '',
    matched                 INTEGER not null default 0,
    manual_review_required  INTEGER not null default 0,
    manual_review_category  TEXT not null default '',
    matched_query           TEXT not null default '',
    deterministic_score     REAL,
    winner_store_product_id TEXT,
    winner_store_key        TEXT,
    tie_break_reason        TEXT not null default '',
    candidates_considered   INTEGER not null default 0,
    stores_offering         INTEGER not null default 0,
    elapsed_seconds         REAL not null default 0,
    match_elapsed_seconds   REAL not null default 0,
    primary key (run_key, item_key, source_kind, source_label)
)
"""

__all__ = [
    "CREATE_SCHEMA_META",
    "CREATE_RUNS",
    "CREATE_ITEMS",
    "CREATE_STORES",
    "CREATE_PRODUCTS",
    "CREATE_RUN_ITEMS",
]
