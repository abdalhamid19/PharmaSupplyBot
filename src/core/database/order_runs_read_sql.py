"""SQL statements and column maps for the order-runs read side.

Kept separate from :mod:`src.core.database.order_runs_read` so each file stays
within the audit limit. Every statement is a SELECT; nothing here mutates data.
"""

from __future__ import annotations

LIST_RUNS = """
select r.run_key, r.run_id, r.profile_key, r.command, r.mode,
       r.started_at, r.finished_at, r.total_items,
       coalesce(v.items, 0)    as items,
       coalesce(v.matched, 0)  as matched,
       coalesce(v.flagged, 0)  as flagged,
       coalesce(v.added_to_cart, 0) as added_to_cart,
       coalesce(v.total_ordered, 0) as total_ordered
from runs r
left join v_run_summary v on v.run_key = r.run_key
order by r.started_at desc, r.run_key desc
"""

RUN_FACTS = """
select ri.item_key, i.item_code, i.item_name, ri.requested_qty,
       ri.ordered_qty, ri.status, ri.reason, ri.matched,
       ri.manual_review_required, ri.stores_offering,
       ri.winner_store_key, ri.elapsed_seconds,
       ri.source_kind, ri.source_label
from run_items ri
join items i on i.item_key = ri.item_key
where ri.run_key = ?
order by i.item_name, i.item_code, ri.source_kind, ri.source_label
"""

ITEM_STORES = """
select ris.store_product_id, ris.store_key, s.store_name,
       ris.available_qty, ris.public_price, ris.purchase_price,
       ris.discount_percent, ris.currency, ris.is_winner,
       ris.ordered_qty, ris.rank_by_discount, ris.source
from run_item_stores ris
left join stores s on s.store_key = ris.store_key
where ris.run_key = ? and ris.item_key = ?
order by ris.is_winner desc, ris.rank_by_discount asc, ris.discount_percent desc
"""

MISSED_DISCOUNT = """
with winners as (
    select run_key, item_key, discount_percent as winner_discount
    from run_item_stores where is_winner = 1
),
best as (
    select run_key, item_key, max(discount_percent) as best_discount
    from run_item_stores group by run_key, item_key
)
select w.run_key, w.item_key, i.item_code, i.item_name,
       w.winner_discount, b.best_discount,
       round(b.best_discount - w.winner_discount, 2) as missed
from winners w
join best b on b.run_key = w.run_key and b.item_key = w.item_key
join items i on i.item_key = w.item_key
where b.best_discount > w.winner_discount + 0.01
order by missed desc, i.item_name
"""

RUN_STORE_ROW_COUNT = "select count(*) from run_item_stores where run_key = ?"

QUERY_COLUMNS = {
    "runs": [
        "run_key", "run_id", "profile_key", "command", "mode",
        "started_at", "finished_at", "total_items", "items", "matched",
        "flagged", "added_to_cart", "total_ordered",
    ],
    "items": [
        "item_key", "item_code", "item_name", "requested_qty",
        "ordered_qty", "status", "reason", "matched",
        "manual_review_required", "stores_offering",
        "winner_store_key", "elapsed_seconds",
        "source_kind", "source_label",
    ],
    "stores": [
        "store_product_id", "store_key", "store_name", "available_qty",
        "public_price", "purchase_price", "discount_percent", "currency",
        "is_winner", "ordered_qty", "rank_by_discount", "source",
    ],
    "missed": [
        "run_key", "item_key", "item_code", "item_name",
        "winner_discount", "best_discount", "missed",
    ],
}
