"""Structured rows for order item summary artifacts."""
from __future__ import annotations

from .candidate_identity import candidate_store_product_id


def order_item_summary_row(item, summary, decision, outcome) -> dict[str, object]:
    """Return one compact row describing the final item outcome."""
    match = decision.best_match if decision else None
    candidate = match.data if match else {}
    return {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "status": summary.status,
        "reason": summary.reason,
        "matched": bool(match),
        "matched_product_name_en": candidate.get("productNameEn", ""),
        "matched_product_name_ar": candidate.get("productName", ""),
        "matched_store_product_id": candidate_store_product_id(candidate),
        "matched_query": match.query if match else "",
        "deterministic_score": round(match.score, 6) if match else "",
        **_summary_ai_fields(outcome, summary.status),
    }


def manual_review_required(summary_status: str, outcome) -> bool:
    """Return whether this final item state needs human review."""
    if outcome is not None and outcome.manual_review:
        return True
    return summary_status in {"no-results", "matched-but-unavailable"}


def manual_review_row(item, summary, decision, outcome) -> dict[str, object]:
    """Return a manual-review row with empty human decision columns."""
    row = order_item_summary_row(item, summary, decision, outcome)
    row.update({"manual_decision": "", "manual_reason": "", "correct_store_product_id": ""})
    return row


def text_block(title: str, row: dict[str, object]) -> str:
    """Return one readable text block for a structured artifact row."""
    body = "\n".join(f"{key}={value}" for key, value in row.items())
    return f"\n--- {title} ---\n{body}\n"


def _summary_ai_fields(outcome, summary_status: str) -> dict[str, object]:
    verify = getattr(outcome, "verify_result", {}) or {}
    search = getattr(outcome, "search_result", {}) or {}
    review = getattr(outcome, "review_result", {}) or {}
    return {
        "ai_enabled": outcome is not None,
        "ai_status": getattr(outcome, "status", ""),
        "ai_verified": bool(verify),
        "ai_searched": bool(search),
        "ai_reviewed": bool(review),
        "ai_confidence": getattr(outcome, "confidence", ""),
        "ai_review_confidence": review.get("confidence", ""),
        "ai_model": _first_value((verify, search, review), "model_used"),
        "ai_provider": _first_value((verify, search, review), "provider_used"),
        "manual_review_required": manual_review_required(summary_status, outcome),
        "final_action": _final_action(summary_status, outcome),
    }


def _first_value(results, key: str) -> object:
    return next((result.get(key, "") for result in results if result.get(key)), "")


def _final_action(summary_status: str, outcome) -> str:
    if manual_review_required(summary_status, outcome):
        return "manual_review"
    return summary_status
