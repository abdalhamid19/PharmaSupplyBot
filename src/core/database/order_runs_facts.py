"""Fact-table DDL for per-store snapshots and candidate diagnostics.

``run_item_stores`` is the table that makes historical warehouse analysis
possible: one row per offering store per item per run, with the strategy's
choice flagged by ``is_winner``.
"""

from __future__ import annotations

CREATE_RUN_ITEM_STORES = """
create table if not exists run_item_stores (
    run_key          TEXT not null references runs(run_key) on delete cascade,
    item_key         TEXT not null references items(item_key),
    store_product_id TEXT not null,
    store_key        TEXT not null,
    available_qty    INTEGER not null default 0,
    public_price     REAL,
    purchase_price   REAL,
    discount_percent REAL,
    currency         TEXT not null default '',
    priority         INTEGER,
    is_winner        INTEGER not null default 0,
    ordered_qty      INTEGER not null default 0,
    rank_by_discount INTEGER,
    source           TEXT not null default '',
    captured_at      TEXT not null,
    primary key (run_key, item_key, store_product_id)
)
"""

CREATE_RUN_CANDIDATES = """
create table if not exists run_candidates (
    run_key          TEXT not null references runs(run_key) on delete cascade,
    item_key         TEXT not null references items(item_key),
    candidate_rank   INTEGER not null,
    store_product_id TEXT not null default '',
    name_ar          TEXT not null default '',
    name_en          TEXT not null default '',
    query            TEXT not null default '',
    total_score      REAL,
    accepted         INTEGER not null default 0,
    rejection_reason TEXT not null default '',
    candidate_source TEXT not null default '',
    is_best_match    INTEGER not null default 0,
    primary key (run_key, item_key, candidate_rank)
)
"""

CREATE_INDEXES = (
    "create index if not exists idx_runs_started on runs(started_at desc)",
    "create index if not exists idx_runs_profile on runs(profile_key, run_id)",
    "create index if not exists idx_products_product_id on products(product_id)",
    "create index if not exists idx_products_name_en on products(name_en)",
    "create index if not exists idx_run_items_item on run_items(item_key, run_key)",
    "create index if not exists idx_run_items_status on run_items(status)",
    (
        "create index if not exists idx_run_items_review on run_items("
        "manual_review_required) where manual_review_required = 1"
    ),
    "create index if not exists idx_ris_store on run_item_stores(store_key, run_key)",
    (
        "create index if not exists idx_ris_product on run_item_stores("
        "store_product_id, run_key)"
    ),
    (
        "create index if not exists idx_ris_winner on run_item_stores("
        "run_key, item_key) where is_winner = 1"
    ),
    (
        "create index if not exists idx_ris_discount on run_item_stores("
        "run_key, discount_percent desc)"
    ),
    (
        "create index if not exists idx_ris_rank on run_item_stores("
        "run_key, item_key, rank_by_discount)"
    ),
)

__all__ = [
    "CREATE_RUN_ITEM_STORES",
    "CREATE_RUN_CANDIDATES",
    "CREATE_INDEXES",
]
