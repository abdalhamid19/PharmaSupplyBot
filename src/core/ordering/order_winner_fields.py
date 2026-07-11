"""Winner-field helpers for order summary artifacts."""

from __future__ import annotations

from ..matching.candidate_identity import candidate_store_product_id
from .order_selected_fields import selected_store_discount_fields


def candidate_summary_fields(
    candidate: dict, decision, match, summary=None
) -> dict[str, object]:
    """Return matched-candidate and winner fields for summary artifacts."""
    en_name = _extract_english_name(candidate)
    store_name, discount = _extract_store_info(candidate, summary)
    fields = _winner_identity_fields(candidate, en_name)
    fields.update(selected_store_discount_fields(store_name, discount))
    fields["tie_break_reason"] = _tie_break_reason(decision, match)
    return fields


def _winner_identity_fields(candidate: dict, en_name: str) -> dict[str, object]:
    """Return product, winner id, quantity, and price fields."""
    candidate_id = candidate_store_product_id(candidate)
    public_price = _extract_public_price(candidate)
    sales_price = _extract_sales_price(candidate)
    return {
        "matched_product_name_en": en_name,
        "matched_product_name_ar": candidate.get("productName", ""),
        "matched_product_id": candidate.get("productId", ""),
        "matched_store_product_id": candidate_id,
        "winner_product_id": candidate.get("productId", ""),
        "winner_store_product_id": candidate_id,
        "winner_available_quantity": candidate.get("availableQuantity", ""),
        "winner_sale_price": public_price,
        "winner_Purchase_Price": sales_price,
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


def _extract_sales_price(candidate: dict) -> str:
    """Extract the actual selected sale price."""
    return candidate.get("salePrice") or candidate.get("salesPrice") or ""


def _tie_break_reason(decision, match) -> str:
    if not match or not decision:
        return ""
    return str(getattr(decision, "final_reason", ""))
