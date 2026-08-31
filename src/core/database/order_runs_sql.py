"""UPSERT statements for order-run dimensions and item facts.

Dimension upserts never overwrite a good value with an empty one, and never
touch ``first_seen_at``. Fact upserts replace every column so re-importing a
run corrects the data instead of duplicating it.
"""

from __future__ import annotations

UPSERT_RUN = """
insert into runs
 (run_key, run_id, profile_key, command, started_at, finished_at, mode,
  execution_mode, warehouse_mode, min_discount_pct, matching_risk,
  excel_source, item_workers, artifact_dir, total_items, schema_version)
values
 (:run_key, :run_id, :profile_key, :command, :started_at, :finished_at, :mode,
  :execution_mode, :warehouse_mode, :min_discount_pct, :matching_risk,
  :excel_source, :item_workers, :artifact_dir, :total_items, :schema_version)
on conflict(run_key) do update set
 mode             = excluded.mode,
 execution_mode   = excluded.execution_mode,
 warehouse_mode   = excluded.warehouse_mode,
 min_discount_pct = excluded.min_discount_pct,
 matching_risk    = excluded.matching_risk,
 excel_source     = excluded.excel_source,
 item_workers     = excluded.item_workers,
 artifact_dir     = excluded.artifact_dir
"""

FINISH_RUN = """
update runs set
 finished_at = :finished_at,
 total_items = (select count(*) from run_items where run_key = :run_key)
where run_key = :run_key
"""

UPSERT_ITEM = """
insert into items (item_key, item_code, item_name, first_seen_at, last_seen_at)
values (:item_key, :item_code, :item_name, :first_seen_at, :last_seen_at)
on conflict(item_key) do update set
 item_code    = case when excluded.item_code <> ''
                     then excluded.item_code else items.item_code end,
 item_name    = case when excluded.item_name <> ''
                     then excluded.item_name else items.item_name end,
 last_seen_at = excluded.last_seen_at
"""

UPSERT_RUN_ITEM = """
insert into run_items
 (run_key, item_key, requested_qty, ordered_qty, status, reason, matched,
  manual_review_required, manual_review_category, matched_query,
  deterministic_score, winner_store_product_id, winner_store_key,
  tie_break_reason, candidates_considered, stores_offering,
  elapsed_seconds, match_elapsed_seconds)
values
 (:run_key, :item_key, :requested_qty, :ordered_qty, :status, :reason, :matched,
  :manual_review_required, :manual_review_category, :matched_query,
  :deterministic_score, :winner_store_product_id, :winner_store_key,
  :tie_break_reason, :candidates_considered, :stores_offering,
  :elapsed_seconds, :match_elapsed_seconds)
on conflict(run_key, item_key) do update set
 requested_qty          = excluded.requested_qty,
 ordered_qty            = excluded.ordered_qty,
 status                 = excluded.status,
 reason                 = excluded.reason,
 matched                = excluded.matched,
 manual_review_required = excluded.manual_review_required,
 manual_review_category = excluded.manual_review_category,
 matched_query          = excluded.matched_query,
 deterministic_score    = excluded.deterministic_score,
 winner_store_product_id = excluded.winner_store_product_id,
 winner_store_key       = excluded.winner_store_key,
 tie_break_reason       = excluded.tie_break_reason,
 candidates_considered  = excluded.candidates_considered,
 stores_offering        = excluded.stores_offering,
 elapsed_seconds        = excluded.elapsed_seconds,
 match_elapsed_seconds  = excluded.match_elapsed_seconds
"""

SELECT_RUN_ITEM_COUNT = "select count(*) from run_items where run_key = ?"
SELECT_RUN_EXISTS = "select 1 from runs where run_key = ?"

__all__ = [
    "UPSERT_RUN",
    "FINISH_RUN",
    "UPSERT_ITEM",
    "UPSERT_RUN_ITEM",
    "SELECT_RUN_ITEM_COUNT",
    "SELECT_RUN_EXISTS",
]
