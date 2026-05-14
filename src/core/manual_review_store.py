"""SQLite persistence for human-approved manual-review matching decisions."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .manual_review_hints import hint_key
from .manual_review_store_sql import (
    ALTER_DECISIONS_TABLE,
    CREATE_DECISIONS_TABLE,
    SELECT_DECISIONS,
    UPSERT_DECISION,
)

DEFAULT_MANUAL_REVIEW_DB = Path("data") / "manual_review" / "manual_review.sqlite3"

@dataclass(frozen=True)
class ManualReviewDecision:
    """One saved manual-review correction for future matching runs."""

    item_code: str
    item_name: str
    approved: bool
    correct_store_product_id: str = ""
    correct_product_name: str = ""
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
    """Small SQLite store for reusable manual-review decisions."""

    def __init__(self, path: Path = DEFAULT_MANUAL_REVIEW_DB):
        """Open a store at the requested path and create its schema."""
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def upsert(self, decision: ManualReviewDecision) -> None:
        """Insert or replace one manual-review decision by normalized item key."""
        code_key, name_key = hint_key(decision.item_code, decision.item_name)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                UPSERT_DECISION, _decision_values(code_key, name_key, decision)
            )

    def lookup(self, item_code: str, item_name: str) -> ManualReviewDecision | None:
        """Return a previously saved decision for an item when one exists."""
        code_key, name_key = hint_key(item_code, item_name)
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                SELECT_DECISIONS + " where item_code_key=? and item_name_key=?",
                (code_key, name_key),
            ).fetchone()
        return _decision_from_row(row) if row else None

    def list_decisions(self) -> list[ManualReviewDecision]:
        """Return all saved manual-review decisions in newest-updated order."""
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                SELECT_DECISIONS + " order by updated_at desc"
            ).fetchall()
        return [_decision_from_row(row) for row in rows]

    def _init_schema(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(CREATE_DECISIONS_TABLE)
            _ensure_manual_decision_column(connection)

def _decision_values(code_key: str, name_key: str, decision: ManualReviewDecision):
    return (
        code_key, name_key, decision.item_code, decision.item_name,
        int(decision.approved), decision.manual_decision,
        decision.correct_store_product_id,
        decision.correct_product_name, decision.correct_query, decision.run_id,
    )

def _decision_from_row(row) -> ManualReviewDecision:
    return ManualReviewDecision(
        row[0], row[1], bool(row[2]), row[3], row[5], row[6], row[7], row[4]
    )

def _ensure_manual_decision_column(connection) -> None:
    columns = _table_columns(connection)
    if "manual_decision" not in columns:
        connection.execute(ALTER_DECISIONS_TABLE)


def _table_columns(connection) -> set[str]:
    rows = connection.execute("pragma table_info(manual_review_decisions)")
    return {row[1] for row in rows}
