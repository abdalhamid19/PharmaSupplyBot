"""SQL statements for the manual-review SQLite store."""

SELECT_DECISIONS = (
    "select item_code,item_name,approved,correct_store_product_id,manual_decision,"
    "correct_product_name,correct_product_name_ar,correct_query,run_id,excel_target_key,"
    "excel_target_source_file,matching_source,matching_source_label,"
    "identity_evidence_kind,identity_evidence,supplier_scope_key,"
    "last_rebind_status,excel_target_row_key,excel_target_source_row,"
    "candidate_method,review_status from manual_review_decisions"
)

UPSERT_DECISION = """
insert into manual_review_decisions
(item_code_key,item_name_key,item_code,item_name,approved,manual_decision,
 correct_store_product_id,correct_product_name,correct_product_name_ar,correct_query,run_id,
 excel_target_key,excel_target_source_file,matching_source,matching_source_label,
 identity_evidence_kind,identity_evidence,supplier_scope_key,last_rebind_status,
 excel_target_row_key,excel_target_source_row,candidate_method,review_status)
values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
on conflict(item_code_key,item_name_key,matching_source,supplier_scope_key) do update set
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
supplier_scope_key=excluded.supplier_scope_key,
last_rebind_status=excluded.last_rebind_status,
excel_target_row_key=excluded.excel_target_row_key,
excel_target_source_row=excluded.excel_target_source_row,
candidate_method=excluded.candidate_method,
review_status=excluded.review_status,
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
    supplier_scope_key TEXT not null default '',
    last_rebind_status TEXT not null default '',
    excel_target_row_key TEXT not null default '',
    excel_target_source_row INTEGER not null default 0,
    candidate_method TEXT not null default '',
    review_status TEXT not null default '',
    created_at TEXT not null default CURRENT_TIMESTAMP,
    updated_at TEXT not null default CURRENT_TIMESTAMP,
    primary key (
        item_code_key, item_name_key, matching_source, supplier_scope_key
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

ALTER_DECISIONS_TABLE_SCOPE = (
    "alter table manual_review_decisions "
    "add column supplier_scope_key TEXT not null default ''"
)

ALTER_DECISIONS_TABLE_REBIND = (
    "alter table manual_review_decisions "
    "add column last_rebind_status TEXT not null default ''"
)

ALTER_DECISIONS_TABLE_ROW_KEY = (
    "alter table manual_review_decisions "
    "add column excel_target_row_key TEXT not null default ''"
)

ALTER_DECISIONS_TABLE_SOURCE_ROW = (
    "alter table manual_review_decisions "
    "add column excel_target_source_row INTEGER not null default 0"
)

ALTER_DECISIONS_TABLE_CANDIDATE_METHOD = (
    "alter table manual_review_decisions "
    "add column candidate_method TEXT not null default ''"
)

ALTER_DECISIONS_TABLE_REVIEW_STATUS = (
    "alter table manual_review_decisions "
    "add column review_status TEXT not null default ''"
)

CREATE_SOURCE_HISTORY_TABLE = """
create table if not exists manual_review_source_history (
    item_code_key TEXT not null,
    item_name_key TEXT not null,
    matching_source TEXT not null,
    supplier_scope_key TEXT not null,
    source_file TEXT not null default '',
    source_label TEXT not null default '',
    run_id TEXT not null default '',
    store_product_id TEXT not null default '',
    product_name TEXT not null default '',
    manual_decision TEXT not null default '',
    rebind_status TEXT not null default '',
    first_seen_at TEXT not null default CURRENT_TIMESTAMP,
    last_seen_at TEXT not null default CURRENT_TIMESTAMP,
    primary key (
        item_code_key,item_name_key,matching_source,supplier_scope_key,
        source_file,store_product_id
    )
)
"""

UPSERT_SOURCE_HISTORY = """
insert into manual_review_source_history
(item_code_key,item_name_key,matching_source,supplier_scope_key,source_file,
 source_label,run_id,store_product_id,product_name,manual_decision,rebind_status)
values (?,?,?,?,?,?,?,?,?,?,?)
on conflict(item_code_key,item_name_key,matching_source,supplier_scope_key,
 source_file,store_product_id) do update set
source_label=excluded.source_label,run_id=excluded.run_id,
product_name=excluded.product_name,manual_decision=excluded.manual_decision,
rebind_status=excluded.rebind_status,last_seen_at=CURRENT_TIMESTAMP
"""
