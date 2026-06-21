"""Winner-field helpers for order summary artifacts."""

from __future__ import annotations

from .candidate_identity import candidate_store_product_id


def candidate_summary_fields(candidate: dict, decision, match) -> dict[str, object]:
    """Return matched-candidate and winner fields for summary artifacts."""
    candidate_id = candidate_store_product_id(candidate)
    
    # FIX: Use fallback English name for DOM candidates (Browser mode)
    # NOTE: Tawreed UI doesn't display English names in the product table,
    # so DOM scraping only captures Arabic names. productNameEnFallback provides
    # a normalized English representation generated from the query or Arabic name.
    en_name = (
        candidate.get("productNameEn") 
        or candidate.get("productNameEnFallback") 
        or ""
    )
    
    return {
        "matched_product_name_en": en_name,
        "matched_product_name_ar": candidate.get("productName", ""),
        "matched_product_id": candidate.get("productId", ""),
        "matched_store_product_id": candidate_id,
        "winner_product_id": candidate.get("productId", ""),
        "winner_store_product_id": candidate_id,
        "winner_available_quantity": candidate.get("availableQuantity", ""),
        "winner_sale_price": candidate.get("salePrice", ""),
        "winner_store_name": candidate.get("storeName", ""),
        "tie_break_reason": _tie_break_reason(decision, match),
    }


def _tie_break_reason(decision, match) -> str:
    if not match or not decision:
        return ""
    return str(getattr(decision, "final_reason", ""))
