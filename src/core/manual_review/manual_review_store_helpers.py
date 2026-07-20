"""Helper functions for manual review store."""

from __future__ import annotations

from .manual_review_store_sql import ALTER_DECISIONS_TABLE, ALTER_DECISIONS_TABLE_AR


def _clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def _decision_values(code_key: str, name_key: str, decision):
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


def _decision_from_row(row):
    from .manual_review_store import ManualReviewDecision
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
    """Add a column when missing (SQLite PRAGMA table_info)."""
    rows = db.execute_query("PRAGMA table_info(manual_review_decisions)")
    # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
    names = {row[1] for row in rows}
    if column not in names:
        db.execute_update(alter_query)


def _default_decision(approved: bool) -> str:
    return "approved_match" if approved else ""


__all__ = [
    "_clean",
    "_decision_values",
    "_decision_from_row",
    "_ensure_column",
    "_default_decision",
]
