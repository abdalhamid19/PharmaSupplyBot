"""Helper functions for manual review store."""

from __future__ import annotations

from .manual_review_store_sql import ALTER_DECISIONS_TABLE, ALTER_DECISIONS_TABLE_AR


def _clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def _decision_values(code_key: str, name_key: str, decision):
    matching_source = _clean(decision.matching_source).lower().replace("_", "-")
    if not matching_source:
        matching_source = (
            "excel-target" if _clean(decision.excel_target_key) else "legacy-unknown"
        )
    supplier_scope_key = _clean(getattr(decision, "supplier_scope_key", ""))
    if not supplier_scope_key:
        if matching_source == "excel-target":
            supplier_scope_key = _clean(decision.excel_target_key)
        elif matching_source == "tawreed":
            supplier_scope_key = _clean(decision.matching_source_label)
        else:
            supplier_scope_key = matching_source
    supplier_scope_key = " ".join(supplier_scope_key.split()).casefold()
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
        decision.excel_target_key,
        decision.excel_target_source_file,
        matching_source,
        decision.matching_source_label,
        decision.identity_evidence_kind,
        decision.identity_evidence,
        supplier_scope_key,
        _clean(getattr(decision, "last_rebind_status", "")),
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
        _clean(row[9]) if len(row) > 9 else "",
        _clean(row[10]) if len(row) > 10 else "",
        _clean(row[11]) if len(row) > 11 else "",
        _clean(row[12]) if len(row) > 12 else "",
        _clean(row[13]) if len(row) > 13 else "",
        _clean(row[14]) if len(row) > 14 else "",
        _clean(row[15]) if len(row) > 15 else "",
        _clean(row[16]) if len(row) > 16 else "",
    )


def _history_values(code_key: str, name_key: str, decision):
    values = _decision_values(code_key, name_key, decision)
    return (
        code_key,
        name_key,
        values[13],
        values[17],
        _clean(decision.excel_target_source_file),
        _clean(decision.matching_source_label),
        _clean(decision.run_id),
        _clean(decision.correct_store_product_id),
        _clean(decision.correct_product_name or decision.correct_product_name_ar),
        _clean(decision.manual_decision),
        values[18],
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
    "_history_values",
]
