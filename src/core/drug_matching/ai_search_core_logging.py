"""Logging functions for AI search core."""

from __future__ import annotations

import logging

logger = logging.getLogger("pharmasupplybot.matching")


def _log_search_skip(trace, code, drug_name, norm, brand, row, reason):
    """Log a search skip event."""
    if trace and trace.enabled:
        trace.log_ai_skip(
            code, drug_name, norm, brand,
            "search", reason,
            row_index=row.name,
        )


def _log_search_not_eligible(trace, code, drug_name, norm, brand, row, cfg):
    """Log a search not eligible event."""
    if trace and trace.enabled:
        trace.log_ai_search_not_eligible(
            code, drug_name, norm, brand,
            (
                "ai_search_skipped_not_eligible: "
                f"no candidate >= {cfg.ai_search_min_candidate_score} "
                "with safe components"
            ),
            row_index=row.name,
        )


def _log_search_sent(trace, verifier, code, drug_name, norm, brand, candidates, price, row):
    """Log search sent event."""
    if trace and trace.enabled:
        from .pricing import price_context
        cand_names = [c[0]["product_name_en"] for c in candidates]
        model = verifier._cfg.model
        trace.log_ai_search_sent(
            code, drug_name, norm, brand,
            len(candidates), cand_names,
            ai_model=model,
            price_context=price_context(price, None),
            row_index=row.name,
        )


def _log_search_failure(trace, code, drug_name, norm, brand, row, ai_result, verifier):
    """Log search failure event."""
    from .ai_search_trace import _search_error_code
    
    if trace and trace.enabled:
        if ai_result:
            confidence = ai_result.get("confidence", 0)
        else:
            confidence = 0
        error_code = _search_error_code(ai_result, confidence, 0.75)
        if hasattr(ai_result, 'get'):
            if ai_result.get("_component_reason") == "unsafe_component_mismatch":
                error_code = "unsafe_component_mismatch"
        trace.log_ai_search_result(
            code, drug_name, norm, brand,
            False, None, confidence,
            model_used=ai_result.get("model_used", "") if ai_result else "",
            api_failures=verifier.get_fallback_log(),
            accept_threshold=0.75,
            row_index=row.name,
            error_code=error_code,
            parse_failed=ai_result.get("parse_failed", False) if ai_result else False,
        )


__all__ = [
    "_log_search_skip",
    "_log_search_not_eligible",
    "_log_search_sent",
    "_log_search_failure",
]
