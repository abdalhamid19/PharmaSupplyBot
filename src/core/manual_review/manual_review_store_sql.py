"""SQL statements for the manual-review CockroachDB store."""

SELECT_DECISIONS = (
    "select item_code,item_name,approved,correct_store_product_id,manual_decision,"
    "correct_product_name,correct_product_name_ar,correct_query,run_id from manual_review_decisions"
)

UPSERT_DECISION = """
insert into manual_review_decisions
(item_code_key,item_name_key,item_code,item_name,approved,manual_decision,
 correct_store_product_id,correct_product_name,correct_product_name_ar,correct_query,run_id)
values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
on conflict(item_code_key,item_name_key) do update set
approved=excluded.approved,
manual_decision=excluded.manual_decision,
correct_store_product_id=excluded.correct_store_product_id,
correct_product_name=excluded.correct_product_name,
correct_product_name_ar=excluded.correct_product_name_ar,
correct_query=excluded.correct_query,
run_id=excluded.run_id,
updated_at=current_timestamp
"""

CREATE_DECISIONS_TABLE = """
create table if not exists manual_review_decisions (
    item_code_key STRING not null,
    item_name_key STRING not null,
    item_code STRING not null,
    item_name STRING not null,
    approved INT not null,
    manual_decision STRING not null default '',
    correct_store_product_id STRING not null default '',
    correct_product_name STRING not null default '',
    correct_product_name_ar STRING not null default '',
    correct_query STRING not null default '',
    run_id STRING not null default '',
    created_at TIMESTAMP not null default current_timestamp,
    updated_at TIMESTAMP not null default current_timestamp,
    primary key (item_code_key, item_name_key)
)
"""

ALTER_DECISIONS_TABLE = (
    "alter table manual_review_decisions "
    "add column if not exists manual_decision STRING not null default ''"
)

ALTER_DECISIONS_TABLE_AR = (
    "alter table manual_review_decisions "
    "add column if not exists correct_product_name_ar STRING not null default ''"
)
