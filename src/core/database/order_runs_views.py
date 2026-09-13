"""Reporting views for the order-runs database.

The joins live here rather than in query or UI code so a schema change touches
one place instead of every call site.
"""

from __future__ import annotations

CREATE_V_RUN_WINNERS = """
create view if not exists v_run_winners as
select r.run_key, r.run_id, r.profile_key, r.started_at,
       i.item_code, i.item_name,
       ri.requested_qty, ri.ordered_qty, ri.status, ri.reason,
       s.store_name, p.name_en, p.name_ar,
       ris.available_qty, ris.public_price, ris.purchase_price,
       ris.discount_percent, ris.currency
from run_items ri
join runs  r on r.run_key  = ri.run_key
join items i on i.item_key = ri.item_key
left join run_item_stores ris
       on ris.run_key   = ri.run_key
      and ris.item_key  = ri.item_key
      and ris.is_winner = 1
left join stores   s on s.store_key        = ris.store_key
left join products p on p.store_product_id = ris.store_product_id
"""

CREATE_V_BEST_DISCOUNT = """
create view if not exists v_best_discount_per_item as
select run_key, item_key, store_key, store_product_id,
       discount_percent, purchase_price, public_price, available_qty
from run_item_stores
where rank_by_discount = 1
"""

CREATE_V_RUN_SUMMARY = """
create view if not exists v_run_summary as
with tawreed_runs as (
    select distinct run_key
    from run_items
    where source_kind = 'tawreed'
), scoped_items as (
    select ri.*
    from run_items ri
    left join tawreed_runs tr on tr.run_key = ri.run_key
    where tr.run_key is null or ri.source_kind = 'tawreed'
)
select r.run_key, r.run_id, r.profile_key, r.started_at, r.finished_at, r.mode,
       count(distinct si.item_key)                                      as items,
       sum(case when si.status != 'not-orderable'
                then si.matched else 0 end)                             as matched,
       sum(si.manual_review_required)                                    as flagged,
       sum(case when si.status = 'no-results' then 1 else 0 end)         as no_results,
       sum(case when si.status = 'not-orderable' then 1 else 0 end)      as not_orderable,
       sum(case when si.status = 'added-to-cart' then 1 else 0 end)      as added_to_cart,
       sum(case when si.status = 'deferred-to-excel-target'
                then 1 else 0 end)                                      as deferred_to_excel,
       sum(si.ordered_qty)                                               as total_ordered
from runs r
join scoped_items si on si.run_key = r.run_key
group by r.run_key
"""

ALL_VIEWS = (
    CREATE_V_RUN_WINNERS,
    CREATE_V_BEST_DISCOUNT,
    CREATE_V_RUN_SUMMARY,
)

__all__ = [
    "CREATE_V_RUN_WINNERS",
    "CREATE_V_BEST_DISCOUNT",
    "CREATE_V_RUN_SUMMARY",
    "ALL_VIEWS",
]
