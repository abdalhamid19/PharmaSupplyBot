"""CockroachDB persistence for human-approved manual-review matching decisions."""

from __future__ import annotations

from dataclasses import dataclass

from .manual_review_hints import hint_key
from .manual_review_store_sql import (
    ALTER_DECISIONS_TABLE,
    ALTER_DECISIONS_TABLE_AR,
    CREATE_DECISIONS_TABLE,
    SELECT_DECISIONS,
    UPSERT_DECISION,
)
from .database import get_db_manager

DEFAULT_MANUAL_REVIEW_DB = None

@dataclass(frozen=True)
class ManualReviewDecision:
    """One saved manual-review correction for future matching runs."""

    item_code: str
    item_name: str
    approved: bool
    correct_store_product_id: str = ""
    correct_product_name: str = ""
    correct_product_name_ar: str = ""
    correct_query: str = ""
    run_id: str = ""
    manual_decision: str = ""

    def __post_init__(self) -> None:
        """Backfill the explicit decision for old approved-only call sites."""
        if self.manual_decision:
            return
        decision = "approved_match" if self.approved else ""
        object.__setattr__(self, "manual_decision", decision)

class ManualReviewStore:
    """CockroachDB store for reusable manual-review decisions."""

    def __init__(self, path=None):
        """Initialize the store and create its schema. `path` is ignored since we use DB manager."""
        self.db = get_db_manager()
        self._init_schema()

    def upsert(self, decision: ManualReviewDecision) -> None:
        """Insert or replace one manual-review decision by normalized item key."""
        code_key, name_key = hint_key(decision.item_code, decision.item_name)
        self.db.execute_update(
            UPSERT_DECISION, _decision_values(code_key, name_key, decision)
        )

    def lookup(self, item_code: str, item_name: str) -> ManualReviewDecision | None:
        """Return a previously saved decision for an item when one exists."""
        code_key, name_key = hint_key(item_code, item_name)
        
        results = self.db.execute_query(
            SELECT_DECISIONS + " where item_code_key=%s and item_name_key=%s",
            (code_key, name_key)
        )
        return _decision_from_row(results[0]) if results else None

    def delete(self, item_code: str, item_name: str) -> None:
        """Remove a previously saved decision for an item."""
        code_key, name_key = hint_key(item_code, item_name)
        self.db.execute_update(
            "delete from manual_review_decisions where item_code_key=%s and item_name_key=%s",
            (code_key, name_key)
        )

    def list_decisions(self) -> list[ManualReviewDecision]:
        """Return all saved manual-review decisions in newest-updated order."""
        rows = self.db.execute_query(SELECT_DECISIONS + " order by updated_at desc")
        return [_decision_from_row(row) for row in rows]

    def _init_schema(self) -> None:
        self.db.execute_update(CREATE_DECISIONS_TABLE)
        _ensure_manual_decision_column(self.db)
        _ensure_correct_product_name_ar_column(self.db)

def _decision_values(code_key: str, name_key: str, decision: ManualReviewDecision):
    return (
        code_key, name_key, decision.item_code, decision.item_name,
        int(decision.approved), decision.manual_decision,
        decision.correct_store_product_id,
        decision.correct_product_name, decision.correct_product_name_ar,
        decision.correct_query, decision.run_id,
    )

def _decision_from_row(row) -> ManualReviewDecision:
    return ManualReviewDecision(
        row[0], row[1], bool(row[2]), row[3], row[5], row[6], row[7], row[8], row[4]
    )

def _ensure_manual_decision_column(db) -> None:
    columns = _table_columns(db)
    if "manual_decision" not in columns:
        db.execute_update(ALTER_DECISIONS_TABLE)

def _ensure_correct_product_name_ar_column(db) -> None:
    columns = _table_columns(db)
    if "correct_product_name_ar" not in columns:
        db.execute_update(ALTER_DECISIONS_TABLE_AR)

def _table_columns(db) -> set[str]:
    rows = db.execute_query("select column_name from information_schema.columns where table_name = 'manual_review_decisions'")
    return {row[0] for row in rows}
