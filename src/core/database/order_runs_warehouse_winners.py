"""Materialized warehouse winners maintained inside item-write transactions."""

from __future__ import annotations

from .warehouse_winner_selection import (
    RULE_VERSION, currency_code, select_warehouse_winner, source_kind, warehouse_display_name,
)

CREATE_WAREHOUSE_WINNERS = """
create table if not exists run_warehouse_winners (
    run_key TEXT not null references runs(run_key) on delete cascade,
    item_key TEXT not null references items(item_key),
    item_code TEXT not null, item_name TEXT not null,
    requested_qty INTEGER not null,
    store_key TEXT, store_product_id TEXT, store_name TEXT,
    source_kind TEXT, source_label TEXT, product_name TEXT,
    available_qty INTEGER, public_price REAL, discount_percent REAL,
    purchase_price REAL, currency TEXT,
    selection_reason TEXT not null, rule_version INTEGER not null,
    primary key (run_key, item_key)
)
"""

WINNER_COLUMNS = (
    "run_key", "item_key", "item_code", "item_name", "requested_qty",
    "store_key", "store_product_id", "store_name", "source_kind", "source_label",
    "product_name", "available_qty", "public_price", "discount_percent",
    "purchase_price", "currency", "selection_reason", "rule_version",
)

OFFERS_SQL = """
select ris.*, s.store_name, coalesce(nullif(p.name_ar, ''), p.name_en, '') product_name
from run_item_stores ris
left join stores s on s.store_key = ris.store_key
left join products p on p.store_product_id = ris.store_product_id
where ris.run_key = ? and ris.item_key = ?
"""


def refresh_warehouse_winner(conn, run_key: str, item_key: str) -> None:
    """Replace one comparison after all currently saved source offers are visible."""
    facts = conn.execute(
        "select i.item_code, i.item_name, max(ri.requested_qty) "
        "from run_items ri join items i on i.item_key = ri.item_key "
        "where ri.run_key = ? and ri.item_key = ? group by i.item_key",
        (run_key, item_key),
    ).fetchone()
    if facts is None:
        return
    winner, reason = select_warehouse_winner(_offers(conn, run_key, item_key))
    row = _comparison_row(run_key, item_key, facts, winner, reason)
    columns = ", ".join(WINNER_COLUMNS)
    values = ", ".join(f":{key}" for key in WINNER_COLUMNS)
    conn.execute(f"insert or replace into run_warehouse_winners ({columns}) values ({values})", row)


def _offers(conn, run_key: str, item_key: str) -> list[dict]:
    cursor = conn.execute(OFFERS_SQL, (run_key, item_key))
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _comparison_row(run_key, item_key, facts, winner, reason) -> dict:
    row = dict.fromkeys(WINNER_COLUMNS)
    row.update(run_key=run_key, item_key=item_key, item_code=facts[0],
               item_name=facts[1], requested_qty=facts[2],
               selection_reason=reason, rule_version=RULE_VERSION)
    if winner:
        for key in ("store_key", "store_product_id", "store_name", "product_name",
                    "available_qty", "public_price", "discount_percent", "purchase_price"):
            row[key] = winner[key]
        row["source_kind"] = source_kind(winner["source"])
        row["source_label"] = winner.get("source_label", "")
        row["currency"] = currency_code(winner["currency"])
        row["store_name"] = warehouse_display_name(winner)
    return row


def backfill_warehouse_winners(conn) -> None:
    """Build old runs only from their surviving snapshots and facts."""
    keys = conn.execute("select distinct run_key, item_key from run_items").fetchall()
    for run_key, item_key in keys:
        refresh_warehouse_winner(conn, run_key, item_key)
