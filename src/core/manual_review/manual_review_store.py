"""CockroachDB persistence for human-approved manual-review decisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Any

from .database import get_db_manager
from .manual_review_hints import hint_key
from .manual_review_store_sql import (
    CREATE_DECISIONS_TABLE,
    SELECT_DECISIONS,
    UPSERT_DECISION,
    ALTER_DECISIONS_TABLE,
    ALTER_DECISIONS_TABLE_AR,
)
from .manual_review_store_helpers import (
    _decision_values,
    _decision_from_row,
    _ensure_column,
    _default_decision,
)
from .manual_review_store_query import (
    _unique_item_keys,
    _chunks,
    _lookup_many_sql,
    _flat_keys,
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

    _schema_initialized_db_ids: set[int] = set()

    def __init__(self, path: Path | None = None, database_manager=None):
        """Initialize the CockroachDB-backed store; `path` is ignored."""
        self.db = database_manager or get_db_manager()
        self._init_schema_once()

    def upsert(self, decision: ManualReviewDecision) -> None:
        """Insert or replace one manual-review decision by normalized item key."""
        code_key, name_key = hint_key(decision.item_code, decision.item_name)
        self.db.execute_update(
            UPSERT_DECISION, _decision_values(code_key, name_key, decision)
        )

    def upsert_batch(self, decisions: list[ManualReviewDecision]) -> None:
        """Batch insert/update multiple decisions in one transaction (much faster)."""
        if not decisions:
            return
        
        values = [
            _decision_values(*hint_key(d.item_code, d.item_name), d)
            for d in decisions
        ]
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(UPSERT_DECISION, values)
            conn.commit()
            cur.close()

    def lookup(self, item_code: str, item_name: str) -> ManualReviewDecision | None:
        """Return a previously saved decision for an item when one exists."""
        code_key, name_key = hint_key(item_code, item_name)
        rows = self.db.execute_query(
            SELECT_DECISIONS + " where item_code_key=%s and item_name_key=%s",
            (code_key, name_key),
        )
        return _decision_from_row(rows[0]) if rows else None

    def lookup_many(
        self, items: Iterable[Any]
    ) -> dict[tuple[str, str], ManualReviewDecision]:
        """Return saved decisions for many items keyed by normalized item key."""
        keys = _unique_item_keys(items)
        if not keys:
            return {}
        rows = []
        for chunk in _chunks(keys, 100):
            rows.extend(self.db.execute_query(_lookup_many_sql(chunk), _flat_keys(chunk)))
        decisions = [_decision_from_row(row) for row in rows]
        return {
            hint_key(decision.item_code, decision.item_name): decision
            for decision in decisions
        }

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

    def _init_schema_once(self) -> None:
        db_id = id(self.db)
        if db_id in self._schema_initialized_db_ids:
            return
        self._init_schema()
        self._schema_initialized_db_ids.add(db_id)


__all__ = [
    "DEFAULT_MANUAL_REVIEW_DB",
    "ManualReviewDecision",
    "ManualReviewStore",
]
