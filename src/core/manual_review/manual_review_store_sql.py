"""SQL statements for the manual-review SQLite store."""

SELECT_DECISIONS = (
    "select item_code,item_name,approved,correct_store_product_id,manual_decision,"
    "correct_product_name,correct_product_name_ar,correct_query,run_id,excel_target_key,"
    "excel_target_source_file,matching_source,matching_source_label,"
    "identity_evidence_kind,identity_evidence from manual_review_decisions"
)

UPSERT_DECISION = """
insert into manual_review_decisions
(item_code_key,item_name_key,item_code,item_name,approved,manual_decision,
 correct_store_product_id,correct_product_name,correct_product_name_ar,correct_query,run_id,
 excel_target_key,excel_target_source_file,matching_source,matching_source_label,
 identity_evidence_kind,identity_evidence)
values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
on conflict(item_code_key,item_name_key,matching_source,matching_source_label) do update set
approved=excluded.approved,
manual_decision=excluded.manual_decision,
correct_store_product_id=excluded.correct_store_product_id,
correct_product_name=excluded.correct_product_name,
correct_product_name_ar=excluded.correct_product_name_ar,
correct_query=excluded.correct_query,
run_id=excluded.run_id,
excel_target_key=excluded.excel_target_key,
excel_target_source_file=excluded.excel_target_source_file,
matching_source=excluded.matching_source,
matching_source_label=excluded.matching_source_label,
identity_evidence_kind=excluded.identity_evidence_kind,
identity_evidence=excluded.identity_evidence,
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
    excel_target_key TEXT not null default '',
    excel_target_source_file TEXT not null default '',
    matching_source TEXT not null default '',
    matching_source_label TEXT not null default '',
    identity_evidence_kind TEXT not null default '',
    identity_evidence TEXT not null default '',
    created_at TEXT not null default CURRENT_TIMESTAMP,
    updated_at TEXT not null default CURRENT_TIMESTAMP,
    primary key (
        item_code_key, item_name_key, matching_source, matching_source_label
    )
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

ALTER_DECISIONS_TABLE_TARGET = (
    "alter table manual_review_decisions "
    "add column excel_target_key TEXT not null default ''"
)

ALTER_DECISIONS_TABLE_TARGET_SOURCE = (
    "alter table manual_review_decisions "
    "add column excel_target_source_file TEXT not null default ''"
)

ALTER_DECISIONS_TABLE_SOURCE = (
    "alter table manual_review_decisions "
    "add column matching_source TEXT not null default ''"
)

ALTER_DECISIONS_TABLE_SOURCE_LABEL = (
    "alter table manual_review_decisions "
    "add column matching_source_label TEXT not null default ''"
)

ALTER_DECISIONS_TABLE_EVIDENCE_KIND = (
    "alter table manual_review_decisions "
    "add column identity_evidence_kind TEXT not null default ''"
)

ALTER_DECISIONS_TABLE_EVIDENCE = (
    "alter table manual_review_decisions "
    "add column identity_evidence TEXT not null default ''"
)
