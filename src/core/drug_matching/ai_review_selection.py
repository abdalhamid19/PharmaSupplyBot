"""Selection logic for AI review - identifying which items need review."""

import pandas as pd


def _select_for_review(results, cfg):
    """Select AI-verified results for review.
    - Genuine low-confidence decisions (confidence > 0 but < threshold): normal review
    - API-failed decisions (confidence == 0): sent for fresh verification (no first-AI opinion)"""
    ai_verified = results[
        results["verified"].isin(["ai_confirmed", "ai_corrected", "ai_found", "ai_rejected"])
    ].copy()
    if len(ai_verified) == 0:
        return ai_verified
    confidences = pd.to_numeric(ai_verified["ai_confidence"], errors="coerce")
    component_reasons = (
        ai_verified["_ai_component_reason"].fillna("").astype(str)
        if "_ai_component_reason" in ai_verified.columns
        else pd.Series("", index=ai_verified.index)
    )
    component_reasons = component_reasons.replace("nan", "")
    component_review = ai_verified[component_reasons != ""]
    # API-failed items (confidence == 0) need fresh verification
    api_failed = ai_verified[confidences == 0.0]
    # Genuine low-confidence items need normal review
    genuine = ai_verified[confidences > 0.0]
    if len(genuine) > 0:
        genuine_confidences = pd.to_numeric(genuine["ai_confidence"], errors="coerce")
        genuine = genuine[genuine_confidences < cfg.ai_review_threshold]
    # Combine both groups
    return pd.concat([api_failed, genuine, component_review]).drop_duplicates()


def _build_review_items(to_review):
    """Build review items: (drug_a, drug_b, first_decision, first_confidence, first_reason, row_idx, api_failed)."""
    items = []
    for idx, row in to_review.iterrows():
        drug_a = row["drug_name"]
        drug_b = row.get("matched_product_name_en", "")
        drug_b_ar = row.get("matched_product_name_ar", "")
        first_decision = row.get("verified", "")
        first_confidence = pd.to_numeric(row.get("ai_confidence", 0), errors="coerce")
        if pd.isna(first_confidence):
            first_confidence = 0.0
        # Mark items where first AI had API failure (confidence=0 from fallback)
        is_api_failed = first_confidence == 0.0
        component_reason = str(row.get("_ai_component_reason", ""))
        if is_api_failed:
            first_reason = "API unavailable - no first AI decision was made"
        else:
            first_reason = component_reason
        items.append((
            drug_a, drug_b or "", drug_b_ar or "", first_decision,
            first_confidence, first_reason, idx, is_api_failed,
            row.get("_drug_price", ""), row.get("_matched_price", ""),
        ))
    return items
