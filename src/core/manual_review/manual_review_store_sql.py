"""SQL statements for the manual-review SQLite store."""

SELECT_DECISIONS = (
    "select item_code,item_name,approved,correct_store_product_id,manual_decision,"
    "correct_product_name,correct_product_name_ar,correct_query,run_id from manual_review_decisions"
)

UPSERT_DECISION = """
insert into manual_review_decisions
(item_code_key,item_name_key,item_code,item_name,approved,manual_decision,
 correct_store_product_id,correct_product_name,correct_product_name_ar,correct_query,run_id)
values (?,?,?,?,?,?,?,?,?,?,?)
on conflict(item_code_key,item_name_key) do update set
approved=excluded.approved,
manual_decision=excluded.manual_decision,
correct_store_product_id=excluded.correct_store_product_id,
correct_product_name=excluded.correct_product_name,
correct_product_name_ar=excluded.correct_product_name_ar,
correct_query=excluded.correct_query,
run_id=excluded.run_id,
updated_at=CURRENT_TIMESTAMP
"""

CREATE_DECISIONS_TABLE = """
create table if not exists manual_review_decisions (
    item_code_key TEXT not null,
    item_name_key TEXT not null,
    item_code TEXT not null,
    item_name TEXT not null,
    approved INTEGER not null,
    manual_decision TEXT not null default '',
    correct_store_product_id TEXT not null default '',
    correct_product_name TEXT not null default '',
    correct_product_name_ar TEXT not null default '',
    correct_query TEXT not null default '',
    run_id TEXT not null default '',
    created_at TEXT not null default CURRENT_TIMESTAMP,
    updated_at TEXT not null default CURRENT_TIMESTAMP,
    primary key (item_code_key, item_name_key)
)
"""

ALTER_DECISIONS_TABLE = (
    "alter table manual_review_decisions "
    "add column manual_decision TEXT not null default ''"
)

ALTER_DECISIONS_TABLE_AR = (
    "alter table manual_review_decisions "
    "add column correct_product_name_ar TEXT not null default ''"
)
