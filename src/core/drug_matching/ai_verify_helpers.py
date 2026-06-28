"""Helper functions for AI verification."""

from __future__ import annotations

import pandas as pd


_FUZZY_VERIFY_METHODS = frozenset((
    "token_set_ratio",
    "token_sort_ratio",
    "partial_token_sort_ratio",
))


def _internal_value(results: pd.DataFrame, idx, col: str, default=""):
    return results.at[idx, col] if col in results.columns else default


def _set_internal_matched_price(results: pd.DataFrame, idx, value):
    if "_matched_price" in results.columns:
        results["_matched_price"] = results["_matched_price"].astype(object)
    results.at[idx, "_matched_price"] = value


def _trace_api_attempts(trace, results, idx, parsed, item):
    if trace and trace.enabled:
        trace.log_api_attempts(
            results.at[idx, "code"], results.at[idx, "drug_name"],
            parsed.normalized, parsed.brand,
            item.get("_api_attempts", []), row_index=idx,
        )


def _trace_parse_failure(trace, results, idx, parsed, item):
    if trace and trace.enabled and item.get("parse_failed"):
        trace.log_ai_parse_failure(
            results.at[idx, "code"], results.at[idx, "drug_name"],
            parsed.normalized, parsed.brand,
            item.get("reason", ""),
            model_used=item.get("model_used", ""),
            row_index=idx,
        )


def _trace_skip_all_verify(results, trace, reason):
    """Log AI verify skip for all eligible drugs."""
    from .normalizer import parse_drug
    matched = results[results["matched_product_name_en"] != ""]
    scores = pd.to_numeric(matched["match_score"], errors="coerce")
    eligible = matched[scores < 90]
    for idx, row in eligible.iterrows():
        parsed = parse_drug(row["drug_name"])
        trace.log_ai_skip(
            row["code"], row["drug_name"],
            parsed.normalized, parsed.brand,
            "verify", reason, row_index=idx,
        )


def _apply_correction(results, idx, ai_result):
    rec = ai_result["record"]
    results.at[idx, "matched_product_name_en"] = rec["product_name_en"]
    results.at[idx, "matched_product_name_ar"] = rec["product_name_ar"]
    results.at[idx, "matched_store_product_id"] = rec["store_product_id"]
    results.at[idx, "match_score"] = round(ai_result["score"], 1)
    results.at[idx, "verified"] = "ai_corrected"
    results.at[idx, "match_method"] = "ai_verified"
    results.at[idx, "ai_confidence"] = round(ai_result.get("confidence", 0), 2)
    _set_internal_matched_price(results, idx, rec.get("price", ""))


def _clear_match(results, idx):
    for col in (
        "matched_product_name_en", "matched_product_name_ar",
        "matched_store_product_id", "match_score", "_matched_price",
    ):
        if col not in results.columns:
            continue
        results[col] = results[col].astype(object)
        results.at[idx, col] = ""
