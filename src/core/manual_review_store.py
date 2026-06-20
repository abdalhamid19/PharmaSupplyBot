"""CockroachDB persistence for human-approved manual-review decisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .database import get_db_manager
from .manual_review_hints import hint_key
from .manual_review_store_sql import (
    ALTER_DECISIONS_TABLE,
    ALTER_DECISIONS_TABLE_AR,
    CREATE_DECISIONS_TABLE,
    SELECT_DECISIONS,
    UPSERT_DECISION,
)

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
        if not self.manual_decision:
            object.__setattr__(self, "manual_decision", _default_decision(self.approved))


class ManualReviewStore:
    """CockroachDB store for reusable manual-review decisions."""

    def __init__(self, path: Path | None = None, database_manager=None):
        """Initialize the CockroachDB-backed store; `path` is ignored."""
        self.db = database_manager or get_db_manager()
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
        rows = self.db.execute_query(
            SELECT_DECISIONS + " where item_code_key=%s and item_name_key=%s",
            (code_key, name_key),
        )
        return _decision_from_row(rows[0]) if rows else None

    def delete(self, item_code: str, item_name: str) -> None:
        """Remove a previously saved decision for an item."""
        code_key, name_key = hint_key(item_code, item_name)
        self.db.execute_update(
            "delete from manual_review_decisions where item_code_key=%s and item_name_key=%s",
            (code_key, name_key),
        )

    def list_decisions(self) -> list[ManualReviewDecision]:
        """Return all saved manual-review decisions in newest-updated order."""
        rows = self.db.execute_query(SELECT_DECISIONS + " order by updated_at desc")
        return [_decision_from_row(row) for row in rows]

    def _init_schema(self) -> None:
        self.db.execute_update(CREATE_DECISIONS_TABLE)
        _ensure_column(self.db, "manual_decision", ALTER_DECISIONS_TABLE)
        _ensure_column(self.db, "correct_product_name_ar", ALTER_DECISIONS_TABLE_AR)


def _decision_values(code_key: str, name_key: str, decision: ManualReviewDecision):
    return (
        code_key,
        name_key,
        decision.item_code,
        decision.item_name,
        int(decision.approved),
        decision.manual_decision,
        decision.correct_store_product_id,
        decision.correct_product_name,
        decision.correct_product_name_ar,
        decision.correct_query,
        decision.run_id,
    )


def _decision_from_row(row) -> ManualReviewDecision:
    return ManualReviewDecision(
        _clean(row[0]),
        _clean(row[1]),
        bool(row[2]),
        _clean(row[3]),
        _clean(row[5]),
        _clean(row[6]),
        _clean(row[7]),
        _clean(row[8]),
        _clean(row[4]),
    )


def _ensure_column(db, column: str, alter_query: str) -> None:
    rows = db.execute_query(
        "select column_name from information_schema.columns "
        "where table_name = 'manual_review_decisions'"
    )
    if column not in {row[0] for row in rows}:
        db.execute_update(alter_query)


def _default_decision(approved: bool) -> str:
    return "approved_match" if approved else ""


def _clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text
