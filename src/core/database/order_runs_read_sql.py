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
       coalesce(v.no_results, 0)    as no_results,
       coalesce(v.not_orderable, 0) as not_orderable,
       coalesce(v.added_to_cart, 0) as added_to_cart,
       coalesce(v.deferred_to_excel, 0) as deferred_to_excel,
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
       ri.matched_name_ar, ri.matched_name_en,
       ri.source_kind, ri.source_label
from run_items ri
join items i on i.item_key = ri.item_key
where ri.run_key = ?
  and (
      ri.source_kind = 'tawreed'
      or not exists (
          select 1 from run_items scoped
          where scoped.run_key = ri.run_key
            and scoped.source_kind = 'tawreed'
      )
  )
order by i.item_name, i.item_code, ri.source_kind, ri.source_label
"""

RUN_ACTUAL_BASKET = """
select ris.item_key, i.item_code, i.item_name,
       coalesce(s.store_name, ris.store_key) as store_name,
       ris.store_key, ris.store_product_id,
       ri.requested_qty, ris.ordered_qty,
       ri.status, ri.reason, ris.public_price, ris.purchase_price,
       ris.discount_percent, ris.currency,
       coalesce(
           nullif(ri.matched_name_ar, ''), nullif(ri.matched_name_en, ''),
           i.item_name
       ) as matched_name
from run_item_stores ris
join items i on i.item_key = ris.item_key
join run_items ri on ri.run_key = ris.run_key
                         and ri.item_key = ris.item_key
                         and ri.source_kind = 'tawreed'
left join stores s on s.store_key = ris.store_key
where ris.run_key = ?
  and ris.source in ('store_details', 'search')
  and ris.ordered_qty > 0
order by store_name, i.item_name, i.item_code
"""

RUN_DEFERRED_EXCEL = """
select ri.item_key, i.item_code, i.item_name,
       ri.requested_qty, ri.ordered_qty, ri.status, ri.reason,
       ri.source_kind, ri.source_label,
       excel.source_label as excel_target_source,
       excel.public_price as excel_public_price,
       excel.purchase_price as excel_purchase_price,
       excel.discount_percent as excel_discount_percent,
       coalesce(
           nullif(excel_item.matched_name_ar, ''),
           nullif(excel_item.matched_name_en, ''),
           nullif(ri.matched_name_ar, ''), nullif(ri.matched_name_en, ''),
           i.item_name
       ) as matched_name
from run_items ri
join items i on i.item_key = ri.item_key
join runs r on r.run_key = ri.run_key
left join run_item_stores excel
      on excel.run_key = ri.run_key
      and excel.item_key = ri.item_key
      and excel.rowid = (
          select chosen.rowid
          from run_item_stores chosen
          where chosen.run_key = ri.run_key
            and chosen.item_key = ri.item_key
            and chosen.source in ('excel_target', 'excel-target')
            and chosen.available_qty > 0
            and chosen.purchase_price > 0
            and chosen.purchase_price < 1e308
            and coalesce(chosen.discount_percent, 0) >= coalesce(r.min_discount_pct, 0) - 0.001
          order by chosen.purchase_price, chosen.source_label, chosen.store_product_id
          limit 1
      )
left join run_items excel_item
       on excel_item.run_key = ri.run_key
      and excel_item.item_key = ri.item_key
      and excel_item.source_kind = 'excel-target'
      and excel_item.source_label = excel.source_label
where ri.run_key = ?
  and ri.status = 'deferred-to-excel-target'
order by excel.source_label, i.item_name, i.item_code
"""

RUN_MATCH_ONLY_SIMULATION = """
select r.mode as run_mode, r.warehouse_mode, r.min_discount_pct,
       ri.item_key, i.item_code, i.item_name, ri.requested_qty,
       ri.status, ri.matched, ri.manual_review_required,
       coalesce(nullif(ri.matched_name_ar, ''),
                nullif(ri.matched_name_en, ''), i.item_name) as matched_name,
       ris.store_product_id, ris.store_key,
       coalesce(s.store_name, ris.store_key) as store_name,
       ris.available_qty, ris.public_price, ris.purchase_price,
       ris.discount_percent, ris.source, ris.source_label,
       coalesce(excel_item.matched, 1) as excel_matched,
       coalesce(excel_item.manual_review_required, 0)
           as excel_manual_review_required,
       coalesce(nullif(excel_item.matched_name_ar, ''),
                nullif(excel_item.matched_name_en, ''),
                nullif(p.name_ar, ''), p.name_en, '') as offer_matched_name
from runs r
join run_items ri
  on ri.run_key = r.run_key
 and (
      ri.source_kind = 'tawreed'
      or (
          ri.source_kind = ''
          and not exists (
              select 1 from run_items scoped
              where scoped.run_key = ri.run_key
                and scoped.source_kind = 'tawreed'
          )
      )
 )
join items i on i.item_key = ri.item_key
left join run_item_stores ris
       on ris.run_key = ri.run_key and ris.item_key = ri.item_key
left join stores s on s.store_key = ris.store_key
left join products p on p.store_product_id = ris.store_product_id
left join run_items excel_item
       on excel_item.run_key = ri.run_key
      and excel_item.item_key = ri.item_key
      and excel_item.source_kind = 'excel-target'
      and excel_item.source_label = ris.source_label
      and ris.source in ('excel_target', 'excel-target')
where r.run_key = ?
order by ri.item_key, ris.rowid
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
        "flagged", "no_results", "not_orderable", "added_to_cart",
        "deferred_to_excel", "total_ordered",
    ],
    "items": [
        "item_key", "item_code", "item_name", "requested_qty",
        "ordered_qty", "status", "reason", "matched",
        "manual_review_required", "stores_offering",
        "winner_store_key", "elapsed_seconds",
        "matched_name_ar", "matched_name_en",
        "source_kind", "source_label",
    ],
    "actual_basket": [
        "item_key", "item_code", "item_name", "store_name", "store_key",
        "store_product_id", "requested_qty", "ordered_qty", "status", "reason",
        "public_price", "purchase_price", "discount_percent", "currency",
        "matched_name",
    ],
    "deferred_excel": [
        "item_key", "item_code", "item_name", "requested_qty", "ordered_qty",
        "status", "reason", "source_kind", "source_label",
        "excel_target_source", "excel_public_price", "excel_purchase_price",
        "excel_discount_percent", "matched_name",
    ],
    "match_only_simulation": [
        "run_mode", "warehouse_mode", "min_discount_pct",
        "item_key", "item_code", "item_name", "requested_qty",
        "status", "matched", "manual_review_required", "matched_name",
        "store_product_id", "store_key", "store_name", "available_qty",
        "public_price", "purchase_price", "discount_percent", "source",
        "source_label",
        "excel_matched", "excel_manual_review_required", "offer_matched_name",
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
