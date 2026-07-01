"""Winner-field helpers for order summary artifacts."""

from __future__ import annotations

from ..matching.candidate_identity import candidate_store_product_id


def candidate_summary_fields(candidate: dict, decision, match, summary=None) -> dict[str, object]:
    """Return matched-candidate and winner fields for summary artifacts."""
    candidate_id = candidate_store_product_id(candidate)
    en_name = _extract_english_name(candidate)
    store_name, discount = _extract_store_info(candidate, summary)
    public_price = _extract_public_price(candidate)

    return {
        "matched_product_name_en": en_name,
        "matched_product_name_ar": candidate.get("productName", ""),
        "matched_product_id": candidate.get("productId", ""),
        "matched_store_product_id": candidate_id,
        "winner_product_id": candidate.get("productId", ""),
        "winner_store_product_id": candidate_id,
        "winner_available_quantity": candidate.get("availableQuantity", ""),
        "winner_sale_price": public_price,
        "winner_store_name": store_name,
        "winner_discount": discount,
        "tie_break_reason": _tie_break_reason(decision, match),
    }


def _extract_english_name(candidate: dict) -> str:
    """Extract English name with fallback."""
    return (
        candidate.get("productNameEn") 
        or candidate.get("productNameEnFallback") 
        or ""
    )


def _extract_store_info(candidate: dict, summary) -> tuple[str, str]:
    """Extract store name and discount info."""
    store_name = candidate.get("storeName", "")
    discount = ""
    if summary:
        if getattr(summary, "selected_store_name", ""):
            store_name = summary.selected_store_name
        discount = getattr(summary, "selected_discount_percent", "")
    return store_name, discount


def _extract_public_price(candidate: dict) -> str:
    """Extract public price with fallbacks."""
    return (
        candidate.get("retailPrice") or 
        candidate.get("publicPrice") or 
        candidate.get("price") or 
        candidate.get("sellingPrice") or 
        ""
    )


def _tie_break_reason(decision, match) -> str:
    if not match or not decision:
        return ""
    return str(getattr(decision, "final_reason", ""))
