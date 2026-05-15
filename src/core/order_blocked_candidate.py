"""Helpers for AI-selected order candidates that are not orderable."""

from __future__ import annotations


def effective_order_status(summary_status: str, outcome) -> str:
    """Return the artifact status after applying blocked-candidate semantics."""
    if missing_store_product_id_outcome(outcome):
        return "matched-but-unavailable"
    return summary_status


def blocked_ai_candidate(outcome) -> dict:
    """Return the AI-selected candidate that could not be used for cart actions."""
    if not missing_store_product_id_outcome(outcome):
        return {}
    record = _search_record(outcome)
    raw = record.get("_raw")
    if isinstance(raw, dict) and raw:
        return raw
    return _candidate_from_record(record)


def blocked_candidate_query(outcome) -> str:
    """Return the query that produced the blocked AI candidate."""
    return str(_search_record(outcome).get("_query", ""))


def blocked_candidate_fields(candidate: dict) -> dict[str, object]:
    """Return artifact fields for a non-orderable AI-selected candidate."""
    return {
        "blocked_candidate_name_en": candidate.get("productNameEn", ""),
        "blocked_candidate_name_ar": candidate.get("productName", ""),
        "blocked_candidate_product_id": candidate.get("productId", ""),
        "blocked_candidate_store_product_id": candidate.get("storeProductId", ""),
        "blocked_candidate_available_quantity": candidate.get("availableQuantity", ""),
        "blocked_candidate_sale_price": candidate.get("salePrice", ""),
    }


def candidate_safety_reason(outcome) -> str:
    """Return the concise local safety reason for a blocked order candidate."""
    outcome_reason = str(getattr(outcome, "reason", "") or "")
    if _mentions_missing_store_id(outcome_reason):
        return "missing storeProductId"
    for result in _outcome_results(outcome):
        reason = str(result.get("reason", "") or "")
        if _mentions_missing_store_id(reason):
            return "missing storeProductId"
        if reason.startswith("local_safety:"):
            return reason.removeprefix("local_safety:").strip()
        if "local safety" in reason.lower():
            return reason
    if "local safety" in outcome_reason.lower():
        return outcome_reason
    return ""


def missing_store_product_id_outcome(outcome) -> bool:
    """Return whether an AI result selected a candidate without storeProductId."""
    if _mentions_missing_store_id(str(getattr(outcome, "reason", "") or "")):
        return True
    record = _search_record(outcome)
    store_id = str(record.get("store_product_id", "") or "").strip()
    return bool(record) and not store_id


def _search_record(outcome) -> dict:
    search = getattr(outcome, "search_result", {}) or {}
    record = search.get("record", {}) if isinstance(search, dict) else {}
    return record if isinstance(record, dict) else {}


def _candidate_from_record(record: dict) -> dict:
    return {
        "productNameEn": record.get("product_name_en", ""),
        "productName": record.get("product_name_ar", ""),
        "storeProductId": record.get("store_product_id", ""),
        "salePrice": record.get("price", ""),
    }


def _outcome_results(outcome) -> tuple[dict, dict, dict]:
    return (
        getattr(outcome, "review_result", {}) or {},
        getattr(outcome, "search_result", {}) or {},
        getattr(outcome, "verify_result", {}) or {},
    )


def _mentions_missing_store_id(reason: str) -> bool:
    return "missing storeproductid" in reason.lower()
