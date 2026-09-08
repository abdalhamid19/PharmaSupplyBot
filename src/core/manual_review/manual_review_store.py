"""SQLite persistence for human-approved manual-review decisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Any

from ..database import get_db_manager
from ..database.database_credentials import _DEFAULT_DB_PATH
from .manual_review_hints import hint_key
from .manual_review_store_sql import (
    CREATE_DECISIONS_TABLE,
    SELECT_DECISIONS,
    UPSERT_DECISION,
    ALTER_DECISIONS_TABLE,
    ALTER_DECISIONS_TABLE_AR,
    ALTER_DECISIONS_TABLE_TARGET,
    ALTER_DECISIONS_TABLE_TARGET_SOURCE,
    ALTER_DECISIONS_TABLE_SOURCE,
    ALTER_DECISIONS_TABLE_SOURCE_LABEL,
    ALTER_DECISIONS_TABLE_EVIDENCE_KIND,
    ALTER_DECISIONS_TABLE_EVIDENCE,
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

DEFAULT_MANUAL_REVIEW_DB = _DEFAULT_DB_PATH


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
    excel_target_key: str = ""
    excel_target_source_file: str = ""
    matching_source: str = ""
    matching_source_label: str = ""
    identity_evidence_kind: str = ""
    identity_evidence: str = ""

    def __post_init__(self) -> None:
        """Backfill the explicit decision for old approved-only call sites."""
        if not self.manual_decision:
            object.__setattr__(self, "manual_decision", _default_decision(self.approved))


class ManualReviewStore:
    """SQLite store for reusable manual-review decisions."""

    _schema_initialized_db_ids: set[int] = set()

    def __init__(self, path: Path | str | None = None, database_manager=None):
        """Initialize the store for a SQLite path (or injected database manager)."""
        if database_manager is not None:
            self.db = database_manager
            self.path = getattr(database_manager, "path", path)
        else:
            db_path = Path(path) if path is not None else DEFAULT_MANUAL_REVIEW_DB
            self.path = db_path
            self.db = get_db_manager(db_path)
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

    def lookup(
        self,
        item_code: str,
        item_name: str,
        *,
        matching_source: str | None = None,
        matching_source_label: str | None = None,
        excel_target_key: str | None = None,
    ) -> ManualReviewDecision | None:
        """Return the newest decision matching an item and optional source scope."""
        code_key, name_key = hint_key(item_code, item_name)
        clauses = ["item_code_key=?", "item_name_key=?"]
        params: list[str] = [code_key, name_key]
        if matching_source is not None:
            clauses.append("replace(lower(matching_source),'_','-')=?")
            params.append(_normalize_source(matching_source))
        if matching_source_label is not None:
            clauses.append("matching_source_label=?")
            params.append(str(matching_source_label))
        if excel_target_key is not None:
            clauses.append("excel_target_key=?")
            params.append(str(excel_target_key))
        rows = self.db.execute_query(
            SELECT_DECISIONS
            + " where "
            + " and ".join(clauses)
            + " order by updated_at desc, rowid desc limit 1",
            tuple(params),
        )
        return _decision_from_row(rows[0]) if rows else None

    def lookup_all(
        self, item_code: str, item_name: str
    ) -> list[ManualReviewDecision]:
        """Return every supplier-specific decision saved for one item."""
        code_key, name_key = hint_key(item_code, item_name)
        rows = self.db.execute_query(
            SELECT_DECISIONS
            + " where item_code_key=? and item_name_key=?"
            + " order by updated_at desc, rowid desc",
            (code_key, name_key),
        )
        return [_decision_from_row(row) for row in rows]

    def lookup_many(
        self,
        items: Iterable[Any],
        *,
        matching_source: str | None = None,
        include_legacy: bool = False,
    ) -> dict[tuple[str, str], ManualReviewDecision]:
        """Return one source-appropriate decision per normalized item key.

        When ``include_legacy`` is true, an explicitly scoped decision wins and
        ``legacy-unknown`` is used only as a compatibility fallback.
        """
        keys = _unique_item_keys(items)
        if not keys:
            return {}
        rows = []
        for chunk in _chunks(keys, 100):
            rows.extend(self.db.execute_query(_lookup_many_sql(chunk), _flat_keys(chunk)))
        requested_source = (
            _normalize_source(matching_source)
            if matching_source is not None
            else None
        )
        selected: dict[tuple[str, str], tuple[int, ManualReviewDecision]] = {}
        for row in rows:
            decision = _decision_from_row(row)
            source = _normalize_source(decision.matching_source)
            if requested_source is None:
                rank = 0
            elif source == requested_source:
                rank = 0
            elif include_legacy and source == "legacy-unknown":
                rank = 1
            else:
                continue
            key = hint_key(decision.item_code, decision.item_name)
            if key not in selected or rank < selected[key][0]:
                selected[key] = (rank, decision)
        return {key: ranked[1] for key, ranked in selected.items()}

    def delete(
        self,
        item_code: str,
        item_name: str,
        *,
        matching_source: str | None = None,
        matching_source_label: str | None = None,
    ) -> None:
        """Remove one source-scoped decision, or every source when omitted."""
        code_key, name_key = hint_key(item_code, item_name)
        clauses = ["item_code_key=?", "item_name_key=?"]
        params: list[str] = [code_key, name_key]
        if matching_source is not None:
            clauses.append("replace(lower(matching_source),'_','-')=?")
            params.append(_normalize_source(matching_source))
        if matching_source_label is not None:
            clauses.append("matching_source_label=?")
            params.append(str(matching_source_label))
        self.db.execute_update(
            "delete from manual_review_decisions where " + " and ".join(clauses),
            tuple(params),
        )

    def list_decisions(self) -> list[ManualReviewDecision]:
        """Return all saved manual-review decisions in newest-updated order."""
        rows = self.db.execute_query(SELECT_DECISIONS + " order by updated_at desc")
        return [_decision_from_row(row) for row in rows]

    def _init_schema(self) -> None:
        self.db.execute_update(CREATE_DECISIONS_TABLE)
        _ensure_column(self.db, "manual_decision", ALTER_DECISIONS_TABLE)
        _ensure_column(self.db, "correct_product_name_ar", ALTER_DECISIONS_TABLE_AR)
        _ensure_column(self.db, "excel_target_key", ALTER_DECISIONS_TABLE_TARGET)
        _ensure_column(
            self.db, "excel_target_source_file", ALTER_DECISIONS_TABLE_TARGET_SOURCE
        )
        _ensure_column(self.db, "matching_source", ALTER_DECISIONS_TABLE_SOURCE)
        _ensure_column(
            self.db,
            "matching_source_label",
            ALTER_DECISIONS_TABLE_SOURCE_LABEL,
        )
        _ensure_column(
            self.db,
            "identity_evidence_kind",
            ALTER_DECISIONS_TABLE_EVIDENCE_KIND,
        )
        _ensure_column(
            self.db,
            "identity_evidence",
            ALTER_DECISIONS_TABLE_EVIDENCE,
        )
        # Make provenance explicit for rows written before the source fields
        # existed.  We can prove an Excel target from its scoped key; all
        # other historical rows remain deliberately unknown rather than
        # being mislabelled as Tawreed.
        self.db.execute_update(
            "update manual_review_decisions "
            "set matching_source='excel-target' "
            "where coalesce(matching_source,'')='' "
            "and coalesce(excel_target_key,'')<>''"
        )
        self.db.execute_update(
            "update manual_review_decisions "
            "set matching_source='legacy-unknown' "
            "where coalesce(matching_source,'')='' "
            "and coalesce(excel_target_key,'')=''"
        )
        self._migrate_to_source_scoped_primary_key()

    def _migrate_to_source_scoped_primary_key(self) -> None:
        """Rebuild legacy item-only tables with a per-source primary key."""
        # Lightweight injected managers used by callers/tests may expose only
        # execute_query/execute_update.  Real SQLite managers provide the
        # transactional connection required for a table rebuild.
        if not hasattr(self.db, "get_connection"):
            return
        schema_rows = self.db.execute_query(
            "pragma table_info(manual_review_decisions)"
        )
        primary_key = [
            row[1]
            for row in sorted(schema_rows, key=lambda row: row[5])
            if row[5]
        ]
        expected = [
            "item_code_key",
            "item_name_key",
            "matching_source",
            "matching_source_label",
        ]
        if primary_key == expected:
            return

        scoped_table = "manual_review_decisions_scoped"
        create_scoped = CREATE_DECISIONS_TABLE.replace(
            "manual_review_decisions", scoped_table, 1
        )
        columns = (
            "item_code_key,item_name_key,item_code,item_name,approved,"
            "manual_decision,correct_store_product_id,correct_product_name,"
            "correct_product_name_ar,correct_query,run_id,excel_target_key,"
            "excel_target_source_file,matching_source,matching_source_label,"
            "identity_evidence_kind,identity_evidence,created_at,updated_at"
        )
        with self.db.get_connection() as conn:
            conn.execute("begin immediate")
            try:
                conn.execute(f"drop table if exists {scoped_table}")
                conn.execute(create_scoped)
                conn.execute(
                    f"insert into {scoped_table} ({columns}) "
                    f"select {columns} from manual_review_decisions"
                )
                conn.execute("drop table manual_review_decisions")
                conn.execute(
                    f"alter table {scoped_table} rename to manual_review_decisions"
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def _init_schema_once(self) -> None:
        db_id = id(self.db)
        if db_id in self._schema_initialized_db_ids:
            return
        self._init_schema()
        self._schema_initialized_db_ids.add(db_id)


def _normalize_source(value: object) -> str:
    """Normalize source aliases for scoped lookup and deletion."""
    return str(value or "").strip().lower().replace("_", "-")


__all__ = [
    "DEFAULT_MANUAL_REVIEW_DB",
    "ManualReviewDecision",
    "ManualReviewStore",
]
