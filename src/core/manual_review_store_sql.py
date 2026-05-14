"""SQL statements for the manual-review SQLite store."""

SELECT_DECISIONS = (
    "select item_code,item_name,approved,correct_store_product_id,"
    "correct_product_name,correct_query,run_id from manual_review_decisions"
)

UPSERT_DECISION = """
insert into manual_review_decisions
(item_code_key,item_name_key,item_code,item_name,approved,
 correct_store_product_id,correct_product_name,correct_query,run_id)
values (?,?,?,?,?,?,?,?,?)
on conflict(item_code_key,item_name_key) do update set
approved=excluded.approved,
correct_store_product_id=excluded.correct_store_product_id,
correct_product_name=excluded.correct_product_name,
correct_query=excluded.correct_query,
run_id=excluded.run_id,
updated_at=current_timestamp
"""

CREATE_DECISIONS_TABLE = """
create table if not exists manual_review_decisions (
    item_code_key text not null,
    item_name_key text not null,
    item_code text not null,
    item_name text not null,
    approved integer not null,
    correct_store_product_id text not null default '',
    correct_product_name text not null default '',
    correct_query text not null default '',
    run_id text not null default '',
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp,
    primary key (item_code_key, item_name_key)
)
"""
