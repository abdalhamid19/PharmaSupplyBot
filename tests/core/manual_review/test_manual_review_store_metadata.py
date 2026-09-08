"""Persistence and migration tests for manual-review provenance metadata."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.core.manual_review.manual_review_selection import decision_from_selection
from src.core.manual_review.manual_review_store import ManualReviewDecision, ManualReviewStore
from src.core.manual_review.manual_review_candidates import ReviewCandidateOption
from src.core.utils.excel import Item


def test_round_trip_preserves_source_and_identity_evidence(tmp_path: Path) -> None:
    store = ManualReviewStore(tmp_path / "manual.sqlite3")
    decision = ManualReviewDecision(
        item_code="1",
        item_name="INODEP CAPSULES 30",
        approved=True,
        correct_store_product_id="baraka-1",
        correct_product_name="INODEP 30 CAPS",
        manual_decision="auto_matched",
        excel_target_key="baraka",
        excel_target_source_file="baraka.xlsx",
        matching_source="excel-target",
        matching_source_label="baraka@baraka.xlsx",
        identity_evidence_kind="dictionary",
        identity_evidence="اينوديب -> INODEP",
    )

    store.upsert(decision)
    saved = store.lookup("1", "INODEP CAPSULES 30")

    assert saved is not None
    assert saved.manual_decision == "auto_matched"
    assert saved.matching_source == "excel-target"
    assert saved.matching_source_label == "baraka@baraka.xlsx"
    assert saved.identity_evidence_kind == "dictionary"
    assert saved.identity_evidence == "اينوديب -> INODEP"
    assert saved.excel_target_key == "baraka"
    assert saved.excel_target_source_file == "baraka.xlsx"


def test_same_item_keeps_independent_rows_per_matching_supplier(tmp_path: Path) -> None:
    store = ManualReviewStore(tmp_path / "manual.sqlite3")
    store.upsert(
        ManualReviewDecision(
            item_code="1", item_name="PANTOGAR 60 CAP", approved=True,
            correct_store_product_id="tawreed-1", manual_decision="auto_matched",
            matching_source="tawreed", matching_source_label="wardany",
        )
    )
    store.upsert(
        ManualReviewDecision(
            item_code="1", item_name="PANTOGAR 60 CAP", approved=True,
            correct_store_product_id="baraka-1", manual_decision="auto_matched",
            matching_source="excel-target",
            matching_source_label="baraka@baraka.xlsx",
            excel_target_key="baraka",
        )
    )

    saved = store.list_decisions()

    assert len(saved) == 2
    assert {
        (decision.matching_source, decision.matching_source_label)
        for decision in saved
    } == {
        ("tawreed", "wardany"),
        ("excel-target", "baraka@baraka.xlsx"),
    }
    baraka = store.lookup(
        "1", "PANTOGAR 60 CAP",
        matching_source="excel-target",
        matching_source_label="baraka@baraka.xlsx",
    )
    assert baraka is not None
    assert baraka.correct_store_product_id == "baraka-1"
    batch = store.lookup_many(
        [Item("1", "PANTOGAR 60 CAP", 1)],
        matching_source="tawreed",
        include_legacy=True,
    )
    assert next(iter(batch.values())).correct_store_product_id == "tawreed-1"

    store.delete(
        "1", "PANTOGAR 60 CAP",
        matching_source="tawreed",
        matching_source_label="wardany",
    )
    remaining = store.list_decisions()
    assert len(remaining) == 1
    assert remaining[0].matching_source == "excel-target"


def test_excel_files_with_same_target_share_one_current_decision_and_keep_history(
    tmp_path: Path,
) -> None:
    store = ManualReviewStore(tmp_path / "manual.sqlite3")
    for filename, product_id, run_id in (
        ("البركة.xlsx", "old-code", "run-1"),
        ("البركة خمسة.xlsx", "new-code", "run-2"),
    ):
        store.upsert(
            ManualReviewDecision(
                item_code="1",
                item_name="INODEP CAPSULES 30",
                approved=True,
                correct_store_product_id=product_id,
                correct_product_name="INODEP CAPSULES 30",
                run_id=run_id,
                manual_decision="approved_match",
                excel_target_key="البركة شركات",
                excel_target_source_file=filename,
                matching_source="excel-target",
                matching_source_label=f"البركة شركات@{filename}",
            )
        )

    decisions = store.list_decisions()
    assert len(decisions) == 1
    assert decisions[0].correct_store_product_id == "new-code"
    assert decisions[0].supplier_scope_key == "البركة شركات"
    assert {row.source_file for row in store.list_source_history("1", "INODEP CAPSULES 30")} == {
        "البركة.xlsx",
        "البركة خمسة.xlsx",
    }


def test_legacy_database_is_migrated_without_losing_decision(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.sqlite3"
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        create table manual_review_decisions (
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
            created_at TEXT not null default CURRENT_TIMESTAMP,
            updated_at TEXT not null default CURRENT_TIMESTAMP,
            primary key (item_code_key, item_name_key)
        );
        insert into manual_review_decisions
        (item_code_key,item_name_key,item_code,item_name,approved,manual_decision,
         correct_store_product_id,correct_product_name,run_id)
        values ('1','PANADOL','1','Panadol',1,'approved_match','old-id','Panadol','old-run');
        """
    )
    con.commit()
    con.close()

    store = ManualReviewStore(db_path)
    saved = store.lookup("1", "Panadol")
    columns = {
        row[1] for row in store.db.execute_query(
            "pragma table_info(manual_review_decisions)"
        )
    }

    assert saved is not None
    assert saved.correct_store_product_id == "old-id"
    assert saved.manual_decision == "approved_match"
    assert saved.matching_source == "legacy-unknown"
    assert saved.identity_evidence == ""
    assert {
        "matching_source",
        "matching_source_label",
        "identity_evidence_kind",
        "identity_evidence",
    } <= columns

    store.upsert(
        ManualReviewDecision(
            item_code="1", item_name="Panadol", approved=True,
            correct_store_product_id="new-id", manual_decision="auto_matched",
            matching_source="tawreed", matching_source_label="wardany",
        )
    )
    assert len(store.list_decisions()) == 2


def test_source_label_schema_merges_same_target_and_preserves_both_files(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "source-label.sqlite3"
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        create table manual_review_decisions (
            item_code_key text not null,item_name_key text not null,
            item_code text not null,item_name text not null,approved integer not null,
            manual_decision text not null default '',correct_store_product_id text not null default '',
            correct_product_name text not null default '',correct_product_name_ar text not null default '',
            correct_query text not null default '',run_id text not null default '',
            excel_target_key text not null default '',excel_target_source_file text not null default '',
            matching_source text not null default '',matching_source_label text not null default '',
            identity_evidence_kind text not null default '',identity_evidence text not null default '',
            supplier_scope_key text not null default '',last_rebind_status text not null default '',
            created_at text not null,updated_at text not null,
            primary key(item_code_key,item_name_key,matching_source,matching_source_label)
        );
        insert into manual_review_decisions values
        ('1','INODEP','1','INODEP',1,'auto_matched','old','INODEP','','','r1',
         'baraka','old.xlsx','excel-target','baraka@old.xlsx','','','baraka','',
         '2026-01-02','2026-01-02'),
        ('1','INODEP','1','INODEP',1,'approved_match','approved','INODEP','','','r2',
         'baraka','approved.xlsx','excel-target','baraka@approved.xlsx','','','baraka','',
         '2026-01-01','2026-01-01');
        """
    )
    con.commit()
    con.close()

    store = ManualReviewStore(db_path)

    decisions = store.list_decisions()
    assert len(decisions) == 1
    assert decisions[0].manual_decision == "approved_match"
    assert {row.source_file for row in store.list_source_history("1", "INODEP")} == {
        "old.xlsx",
        "approved.xlsx",
    }
    assert db_path.with_suffix(".sqlite3.supplier-scope-v2.bak").exists()


def test_manual_selection_carries_candidate_provenance() -> None:
    option = ReviewCandidateOption(
        store_product_id="baraka-1",
        name_en="INODEP 30 CAPS",
        name_ar="اينوديب 30 كبسول",
        supplier="Baraka",
        available_quantity=3,
        price=10.0,
        score=20.0,
        rejection_reason="",
        orderable=True,
        matching_source="excel-target",
        matching_source_label="baraka@baraka.xlsx",
        identity_evidence_kind="dictionary",
        identity_evidence="اينوديب -> INODEP",
        excel_target_key="baraka",
        excel_target_source_file="baraka.xlsx",
    )

    decision = decision_from_selection(
        Item("1", "INODEP CAPSULES 30", 1), option, False, "", "run-1"
    )

    assert decision is not None
    assert decision.manual_decision == "approved_match"
    assert decision.matching_source == "excel-target"
    assert decision.matching_source_label == "baraka@baraka.xlsx"
    assert decision.identity_evidence_kind == "dictionary"
    assert decision.excel_target_key == "baraka"
