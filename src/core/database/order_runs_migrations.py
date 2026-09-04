"""Migrations between order-runs schema versions.

The :func:`apply_migrations` function is called from
:class:`src.core.database.order_runs_store.OrderRunsStore` once per database
file. Each migration is a forward-only, idempotent SQL script that brings the
schema from ``N - 1`` to ``N``. The function is no-op when the database is
already at the current :data:`SCHEMA_VERSION`.

Migrations must:

* be safe to re-run (idempotent on the same target version)
* preserve existing data — every historical fact must survive the upgrade
* run inside the same transaction as the schema-version upsert
"""

from __future__ import annotations

from typing import Callable

from .order_runs_version import SCHEMA_VERSION

MigrationFn = Callable[[object], None]


def _migrate_v2_to_v3(conn) -> None:
    """Migrate the run_items table to v3 with source_kind / source_label.

    SQLite cannot alter a primary key in place, so the migration renames
    the old table, recreates it with the new shape, and copies the data
    over. Every legacy row is tagged with ``source_kind='tawreed'`` and
    ``source_label=runs.profile_key`` so the analytics queries can still
    answer "where did this match come from?" for old runs.

    The migration is a no-op when the ``run_items`` table does not yet
    exist (fresh databases go straight to the v3 CREATE statement in
    :data:`ALL_DDL`).
    """
    tables = {
        row[0]
        for row in conn.execute(
            "select name from sqlite_master where type='table'"
        ).fetchall()
    }
    if "run_items" not in tables:
        return
    columns = {row[1] for row in conn.execute("pragma table_info(run_items)").fetchall()}
    if "source_kind" in columns and "source_label" in columns:
        return
    # Drop every view first: views reference the columns we are about
    # to remove, and SQLite refuses to drop a table while a view
    # depends on it. The same view definitions are recreated later by
    # the ALL_DDL statements.
    for row in conn.execute(
        "select name from sqlite_master where type='view'"
    ).fetchall():
        conn.execute(f"drop view if exists {row[0]}")
    if "run_items_v2" in tables:
        # A previous attempt at this migration left a staging table
        # behind. Drop the child tables first (they hold FKs to
        # run_items_v2 after the rename), then drop the staging
        # table. The child tables are recreated later by ALL_DDL.
        for child in ("run_item_stores", "run_candidates"):
            if child in tables:
                conn.execute(f"drop table if exists {child}")
        conn.execute("drop table run_items_v2")
    else:
        # First-time migration: drop child tables so the rename + create
        # below does not collide with their FK on the column shape.
        for child in ("run_item_stores", "run_candidates"):
            if child in tables:
                conn.execute(f"drop table if exists {child}")
    conn.execute("alter table run_items rename to run_items_v2")
    conn.execute(
        """
        create table run_items (
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
    )
    conn.execute(
        """
        insert into run_items (
            run_key, item_key, source_kind, source_label,
            requested_qty, ordered_qty, status, reason, matched,
            manual_review_required, manual_review_category, matched_query,
            deterministic_score, winner_store_product_id, winner_store_key,
            tie_break_reason, candidates_considered, stores_offering,
            elapsed_seconds, match_elapsed_seconds
        )
        select
            v2.run_key, v2.item_key,
            'tawreed' as source_kind,
            coalesce(r.profile_key, '') as source_label,
            v2.requested_qty, v2.ordered_qty, v2.status, v2.reason, v2.matched,
            v2.manual_review_required, v2.manual_review_category, v2.matched_query,
            v2.deterministic_score, v2.winner_store_product_id, v2.winner_store_key,
            v2.tie_break_reason, v2.candidates_considered, v2.stores_offering,
            v2.elapsed_seconds, v2.match_elapsed_seconds
        from run_items_v2 v2
        left join runs r on r.run_key = v2.run_key
        """
    )
    conn.execute("drop table run_items_v2")


def _migrate_v3_to_v4(conn) -> None:
    """Add ``matched_name_ar`` and ``matched_name_en`` to ``run_items``.

    These columns surface the matched product's name (Arabic + English)
    in the Run Results tab so pharmacists can verify what was actually
    matched without opening the offering-store expander. v3 rows simply
    get empty strings; new runs fill the columns at write time.
    """
    tables = {
        row[0]
        for row in conn.execute(
            "select name from sqlite_master where type='table'"
        ).fetchall()
    }
    if "run_items" not in tables:
        return
    columns = {row[1] for row in conn.execute("pragma table_info(run_items)").fetchall()}
    if "matched_name_ar" in columns and "matched_name_en" in columns:
        return
    conn.execute(
        "alter table run_items add column matched_name_ar TEXT not null default ''"
    )
    conn.execute(
        "alter table run_items add column matched_name_en TEXT not null default ''"
    )


def _migrate_v4_to_v5(conn) -> None:
    """Recreate ``v_run_summary`` to include ``not_orderable`` and ``no_results``.

    The v3/v4 view counted only ``items``, ``matched``, ``flagged`` and
    ``added_to_cart``. The Run Results KPI bar exposes a "Not-orderable"
    toggle, but without these columns the bar always read zero. Drop the
    stale view so :data:`ALL_DDL` recreates it with the new shape.
    """
    conn.execute("drop view if exists v_run_summary")


MIGRATIONS: dict[int, MigrationFn] = {
    3: _migrate_v2_to_v3,
    4: _migrate_v3_to_v4,
    5: _migrate_v4_to_v5,
}


def apply_migrations(conn, current_version: int) -> int:
    """Apply every forward migration from ``current_version`` up to SCHEMA_VERSION.

    Returns the new schema version (which equals :data:`SCHEMA_VERSION` when
    the call is a no-op).
    """
    version = max(int(current_version or 0), 0)
    for target in range(version + 1, SCHEMA_VERSION + 1):
        migrate = MIGRATIONS.get(target)
        if migrate is None:
            continue
        migrate(conn)
    return SCHEMA_VERSION


__all__ = ["MIGRATIONS", "apply_migrations", "MigrationFn"]
