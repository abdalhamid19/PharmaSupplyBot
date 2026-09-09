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
        _clean(getattr(decision, "excel_target_row_key", "")),
        _safe_int(getattr(decision, "excel_target_source_row", 0)),
        _clean(getattr(decision, "candidate_method", "")),
        _clean(getattr(decision, "review_status", "")),
    )


def _decision_from_row(row):
    from .manual_review_store import ManualReviewDecision
    raw_manual_decision = _clean(row[4])
    matching_source = _clean(row[11]) if len(row) > 11 else ""
    if (
        not raw_manual_decision
        and bool(row[2])
        and matching_source.casefold().replace("_", "-") == "excel-target"
    ):
        raw_manual_decision = "legacy_approved"
    return ManualReviewDecision(
        _clean(row[0]),
        _clean(row[1]),
        bool(row[2]),
        _clean(row[3]),
        _clean(row[5]),
        _clean(row[6]),
        _clean(row[7]),
        _clean(row[8]),
        raw_manual_decision,
        _clean(row[9]) if len(row) > 9 else "",
        _clean(row[10]) if len(row) > 10 else "",
        _clean(row[11]) if len(row) > 11 else "",
        _clean(row[12]) if len(row) > 12 else "",
        _clean(row[13]) if len(row) > 13 else "",
        _clean(row[14]) if len(row) > 14 else "",
        _clean(row[15]) if len(row) > 15 else "",
        _clean(row[16]) if len(row) > 16 else "",
        _clean(row[17]) if len(row) > 17 else "",
        _safe_int(row[18]) if len(row) > 18 else 0,
        _clean(row[19]) if len(row) > 19 else "",
        _clean(row[20]) if len(row) > 20 else "",
    )


def _history_values(code_key: str, name_key: str, decision):
    return _history_values_from_decision_values(
        code_key,
        name_key,
        decision,
        _decision_values(code_key, name_key, decision),
    )


def _history_values_from_decision_values(
    code_key: str,
    name_key: str,
    decision,
    decision_values: tuple[object, ...],
):
    return (
        code_key,
        name_key,
        decision_values[13],
        decision_values[17],
        _clean(decision.excel_target_source_file),
        _clean(decision.matching_source_label),
        _clean(decision.run_id),
        _clean(decision.correct_store_product_id),
        _clean(decision.correct_product_name or decision.correct_product_name_ar),
        _clean(decision.manual_decision),
        decision_values[18],
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


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def is_scoped_excel_target_approval(
    decision,
    *,
    target_key: str,
    source_file: str,
    source_row: int,
    row_key: str,
) -> bool:
    """Return whether an approval is safe to rebind to one Excel row.

    A legacy item-level approval may still be loaded for compatibility, but it
    deliberately fails this predicate and therefore cannot override a form,
    strength, concentration, or pack conflict.
    """
    if not decision or not decision.approved:
        return False
    if decision.manual_decision != "approved_match":
        return False
    if str(getattr(decision, "matching_source", "")).strip().lower().replace("_", "-") != "excel-target":
        return False
    if not _clean(target_key) or not _clean(getattr(decision, "excel_target_key", "")):
        return False
    return (
        _normalize_scope(getattr(decision, "excel_target_key", ""))
        == _normalize_scope(target_key)
        and _normalize_scope(getattr(decision, "excel_target_source_file", ""))
        == _normalize_scope(source_file, path=True)
        and _safe_int(getattr(decision, "excel_target_source_row", 0))
        == _safe_int(source_row)
        and _clean(getattr(decision, "excel_target_row_key", ""))
        == _clean(row_key)
        and bool(_clean(row_key))
        and bool(_clean(source_file))
        and _safe_int(source_row) > 0
    )


def _normalize_scope(value: object, *, path: bool = False) -> str:
    text = " ".join(str(value or "").strip().casefold().split())
    return text.replace("\\", "/") if path else text


__all__ = [
    "_clean",
    "_decision_values",
    "_decision_from_row",
    "_ensure_column",
    "_default_decision",
    "_history_values",
    "_history_values_from_decision_values",
    "is_scoped_excel_target_approval",
]
