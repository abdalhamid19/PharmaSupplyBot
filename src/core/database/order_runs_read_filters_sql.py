"""Filtered SELECTs powering the Run Results KPI drilldown modals.

Kept separate from :mod:`src.core.database.order_runs_read_sql` so each file
stays within the audit limit. Every statement mirrors the shape of
``RUN_FACTS`` so the returned rows can use the same ``items`` column map.

Each filter is the WHERE clause used by one KPI card on the Run Results
(Database) tab; the rule is the same as :data:`v_run_summary` so the counts in
the modal equal the number on the card.
"""

from __future__ import annotations

RUN_ITEMS_MATCHED = """
select ri.item_key, i.item_code, i.item_name, ri.requested_qty,
       ri.ordered_qty, ri.status, ri.reason, ri.matched,
       ri.manual_review_required, ri.stores_offering,
       ri.winner_store_key, ri.elapsed_seconds,
       ri.matched_name_ar, ri.matched_name_en,
       ri.source_kind, ri.source_label
from run_items ri
join items i on i.item_key = ri.item_key
where ri.run_key = ?
  and ri.matched = 1
  and ri.status != 'not-orderable'
order by i.item_name, i.item_code, ri.source_kind, ri.source_label
"""

RUN_ITEMS_FLAGGED = """
select ri.item_key, i.item_code, i.item_name, ri.requested_qty,
       ri.ordered_qty, ri.status, ri.reason, ri.matched,
       ri.manual_review_required, ri.stores_offering,
       ri.winner_store_key, ri.elapsed_seconds,
       ri.matched_name_ar, ri.matched_name_en,
       ri.source_kind, ri.source_label
from run_items ri
join items i on i.item_key = ri.item_key
where ri.run_key = ?
  and ri.manual_review_required = 1
order by i.item_name, i.item_code, ri.source_kind, ri.source_label
"""

RUN_ITEMS_NOT_ORDERABLE = """
select ri.item_key, i.item_code, i.item_name, ri.requested_qty,
       ri.ordered_qty, ri.status, ri.reason, ri.matched,
       ri.manual_review_required, ri.stores_offering,
       ri.winner_store_key, ri.elapsed_seconds,
       ri.matched_name_ar, ri.matched_name_en,
       ri.source_kind, ri.source_label
from run_items ri
join items i on i.item_key = ri.item_key
where ri.run_key = ?
  and ri.status = 'not-orderable'
order by i.item_name, i.item_code, ri.source_kind, ri.source_label
"""

RUN_ITEMS_ORDERED = """
select ri.item_key, i.item_code, i.item_name, ri.requested_qty,
       ri.ordered_qty, ri.status, ri.reason, ri.matched,
       ri.manual_review_required, ri.stores_offering,
       ri.winner_store_key, ri.elapsed_seconds,
       ri.matched_name_ar, ri.matched_name_en,
       ri.source_kind, ri.source_label
from run_items ri
join items i on i.item_key = ri.item_key
where ri.run_key = ?
  and ri.ordered_qty > 0
order by i.item_name, i.item_code, ri.source_kind, ri.source_label
"""

__all__ = [
    "RUN_ITEMS_MATCHED",
    "RUN_ITEMS_FLAGGED",
    "RUN_ITEMS_NOT_ORDERABLE",
    "RUN_ITEMS_ORDERED",
]