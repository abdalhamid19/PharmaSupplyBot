"""Component mismatch analysis for AI review."""

import re
import pandas as pd
from rapidfuzz import fuzz

from .normalizer import parse_drug


def _component_review_required(results, idx) -> str:
    if "_ai_component_reason" not in results.columns:
        return ""
    reason = results.at[idx, "_ai_component_reason"]
    if reason is None or pd.isna(reason):
        return ""
    reason = str(reason)
    return "" if reason.lower() == "nan" else reason


def _safe_reviewed_component_mismatch(results, idx, cfg, reason: str) -> bool:
    if reason not in {"different_brand", "brand_prefix_mismatch"}:
        return False
    parsed = parse_drug(results.at[idx, "drug_name"])
    matched = parse_drug(results.at[idx, "matched_product_name_en"])
    if _brand_similarity(parsed.brand, matched.brand) < 84:
        return False
    unsafe_checks = (
        parsed.dosage_nums and matched.dosage_nums
        and parsed.dosage_nums != matched.dosage_nums,
        parsed.form and matched.form and parsed.form != matched.form,
        parsed.qty and matched.qty and parsed.qty != matched.qty,
        parsed.volume and matched.volume and parsed.volume != matched.volume,
    )
    if any(unsafe_checks):
        return False
    return True


def _reject_reviewed_component_mismatch(
    verifier, results, idx, parsed, review_confidence, review_reason, trace, rr,
):
    from .ai_verify import _clear_match

    _clear_match(results, idx)
    results.at[idx, "verified"] = "ai_review_rejected"
    results.at[idx, "match_method"] = "ai_reviewed"
    results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
    if trace and trace.enabled:
        trace.log_ai_review_result(
            results.at[idx, "code"], results.at[idx, "drug_name"],
            parsed.normalized, parsed.brand,
            False, review_confidence, review_reason,
            "ai_review_rejected",
            review_model=verifier._cfg.review_model,
            api_failures=verifier.get_fallback_log(),
            row_index=idx,
            parse_failed=rr.get("parse_failed", False),
        )


def _brand_similarity(left: str, right: str) -> float:
    left_clean = re.sub(r"[^A-Z0-9]", "", left)
    right_clean = re.sub(r"[^A-Z0-9]", "", right)
    if not left_clean or not right_clean:
        return 0.0
    if left_clean in right_clean or right_clean in left_clean:
        return 100.0
    return fuzz.ratio(left_clean, right_clean)
