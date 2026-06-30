"""Rejection handling for AI verification."""

from __future__ import annotations

from ..normalization.normalizer import parse_drug
from ..normalization.normalizer_matching import components_match
from .ai_verify_helpers import (
    _internal_value,
    _apply_correction,
    _clear_match,
    _trace_api_attempts,
    _trace_parse_failure,
)


async def _handle_rejected(verifier, results, index, idx, cfg, trace, vr):
    """Handle AI-rejected matches by searching for better alternatives."""
    drug_name = results.at[idx, "drug_name"]
    parsed = parse_drug(drug_name)
    norm = parsed.normalized
    candidates = index.fuzzy_match(norm, top_k=5)
    valid = [
        (rec, score, cidx) for rec, score, cidx in candidates
        if components_match(
            parsed, index.get_parsed(cidx),
            cfg.brand_prefix_min,
        )[0]
    ]
    if valid:
        ai_result = await verifier.find_better_match(
            drug_name, valid,
            inventory_price=_internal_value(results, idx, "_drug_price"),
        )
        if ai_result and ai_result.get("record"):
            _apply_correction(results, idx, ai_result)
            if trace and trace.enabled:
                rec = ai_result["record"]
                trace.log_ai_verify_result(
                    results.at[idx, "code"], drug_name,
                    norm, parsed.brand,
                    False, "ai_corrected",
                    f"AI rejected original, found better: "
                    f"{rec['product_name_en']}",
                    results.at[idx, "matched_product_name_en"],
                    ai_result.get("confidence"),
                    ai_result.get("reason", ""),
                    rec["product_name_en"],
                    model_used=ai_result.get("model_used", ""),
                    api_failures=verifier.get_fallback_log(),
                    row_index=idx,
                    parse_failed=ai_result.get("parse_failed", False),
                )
                _trace_api_attempts(trace, results, idx, parsed, ai_result)
                _trace_parse_failure(trace, results, idx, parsed, ai_result)
            return 1, 0
    _clear_match(results, idx)
    results.at[idx, "verified"] = "ai_rejected"
    results.at[idx, "match_method"] = "ai_verified"
    results.at[idx, "ai_confidence"] = round(vr.get("confidence", 0), 2)
    if trace and trace.enabled:
        trace.log_ai_verify_result(
            results.at[idx, "code"], drug_name,
            norm, parsed.brand,
            False, "ai_rejected",
            "AI rejected and no better match found",
            results.at[idx, "matched_product_name_en"],
            vr.get("confidence"), vr.get("reason", ""),
            "",
            model_used=vr.get("model_used", ""),
            api_failures=verifier.get_fallback_log(),
            row_index=idx,
            parse_failed=vr.get("parse_failed", False),
        )
        _trace_parse_failure(trace, results, idx, parsed, vr)
    return 0, 1


__all__ = ["_handle_rejected"]
