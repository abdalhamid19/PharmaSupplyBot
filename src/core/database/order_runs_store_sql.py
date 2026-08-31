"""UPSERT statements for store snapshots and their dimensions.

Dimension upserts never overwrite a good value with an empty one and never move
``first_seen_at``. The snapshot upsert replaces every measured column so a
re-import corrects the data instead of duplicating it.
"""

from __future__ import annotations

UPSERT_STORE = """
insert into stores (store_key, store_name, first_seen_at, last_seen_at)
values (:store_key, :store_name, :first_seen_at, :last_seen_at)
on conflict(store_key) do update set
 store_name   = case when excluded.store_name <> ''
                     then excluded.store_name else stores.store_name end,
 last_seen_at = excluded.last_seen_at
"""

UPSERT_PRODUCT = """
insert into products
 (store_product_id, product_id, name_ar, name_en, is_synthetic,
  first_seen_at, last_seen_at)
values
 (:store_product_id, :product_id, :name_ar, :name_en, :is_synthetic,
  :first_seen_at, :last_seen_at)
on conflict(store_product_id) do update set
 product_id   = case when excluded.product_id <> ''
                     then excluded.product_id else products.product_id end,
 name_ar      = case when excluded.name_ar <> ''
                     then excluded.name_ar else products.name_ar end,
 name_en      = case when excluded.name_en <> ''
                     then excluded.name_en else products.name_en end,
 is_synthetic = excluded.is_synthetic,
 last_seen_at = excluded.last_seen_at
"""

UPSERT_RUN_ITEM_STORE = """
insert into run_item_stores
 (run_key, item_key, store_product_id, store_key, available_qty, public_price,
  purchase_price, discount_percent, currency, priority, is_winner, ordered_qty,
  rank_by_discount, source, captured_at)
values
 (:run_key, :item_key, :store_product_id, :store_key, :available_qty,
  :public_price, :purchase_price, :discount_percent, :currency, :priority,
  :is_winner, :ordered_qty, :rank_by_discount, :source, :captured_at)
on conflict(run_key, item_key, store_product_id) do update set
 store_key        = excluded.store_key,
 available_qty    = excluded.available_qty,
 public_price     = excluded.public_price,
 purchase_price   = excluded.purchase_price,
 discount_percent = excluded.discount_percent,
 currency         = excluded.currency,
 priority         = excluded.priority,
 is_winner        = excluded.is_winner,
 ordered_qty      = excluded.ordered_qty,
 rank_by_discount = excluded.rank_by_discount,
 source           = excluded.source,
 captured_at      = excluded.captured_at
"""

DELETE_RUN_ITEM_STORES = (
    "delete from run_item_stores where run_key = :run_key and item_key = :item_key"
)

SELECT_RUN_ITEM_STORE_COUNT = (
    "select count(*) from run_item_stores where run_key = ? and item_key = ?"
)

__all__ = [
    "UPSERT_STORE",
    "UPSERT_PRODUCT",
    "UPSERT_RUN_ITEM_STORE",
    "DELETE_RUN_ITEM_STORES",
    "SELECT_RUN_ITEM_STORE_COUNT",
]
