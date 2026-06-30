"""Search execution and result application functions."""

from __future__ import annotations

from .ai_search_candidates import (
    _search_candidates,
    _eligible_search_candidates,
    _search_acceptance_threshold,
    _apply_search_result,
)
from .ai_search_trace import (
    _trace_api_attempts,
    _trace_parse_failure,
)
from .ai_search_core_logging import (
    _log_search_skip,
    _log_search_not_eligible,
    _log_search_sent,
    _log_search_failure,
)


async def _try_search_one(verifier, results, index, row, cfg, trace):
    """Try to search for one unmatched item."""
    from ..normalization.normalizer import parse_drug
    
    drug_name = row["drug_name"]
    parsed = parse_drug(drug_name)
    norm = parsed.normalized
    code = str(row.get("code", ""))
    if not norm or len(norm) < 3:
        _log_search_skip(
            trace, code, drug_name, norm, parsed.brand, row,
            "norm too short for AI search"
        )
        return 0
    price = row.get("_drug_price", "")
    candidates = _search_candidates(parsed, norm, index, cfg, price)
    if not candidates:
        _log_search_skip(
            trace, code, drug_name, norm, parsed.brand, row,
            "no valid candidates found"
        )
        return 0
    candidates = _eligible_search_candidates(parsed, candidates, index, cfg)
    if not candidates:
        _log_search_not_eligible(trace, code, drug_name, norm, parsed.brand, row, cfg)
        return 0
    return await _execute_search_and_apply(
        verifier, results, index, row, parsed, candidates, price, cfg, trace
    )


async def _execute_search_and_apply(
    verifier, results, index, row, parsed, candidates, price, cfg, trace
):
    """Execute AI search and apply result if accepted."""
    drug_name = row["drug_name"]
    code = str(row.get("code", ""))
    norm = parsed.normalized
    _log_search_sent(trace, verifier, code, drug_name, norm, parsed.brand, candidates, price, row)
    ai_result = await verifier.find_better_match(drug_name, candidates, inventory_price=price)
    if ai_result:
        _trace_api_attempts(trace, results, row.name, parsed, ai_result)
        _trace_parse_failure(trace, results, row.name, parsed, ai_result)
        confidence = ai_result.get("confidence", 0) if ai_result else 0
        accept_threshold, acceptance_reason = _search_acceptance_threshold(
            ai_result, candidates, parsed, index, cfg,
        )
        if (
            ai_result and ai_result.get("record")
            and confidence >= accept_threshold
            and acceptance_reason != "unsafe_component_mismatch"
        ):
            return _apply_successful_search(
                results, row, ai_result, acceptance_reason, trace, code, drug_name,
                norm, parsed.brand, confidence, accept_threshold, verifier
            )
    _log_search_failure(trace, code, drug_name, norm, parsed.brand, row, ai_result, verifier)
    return 0


def _apply_successful_search(
    results, row, ai_result, acceptance_reason, trace, code, drug_name,
    norm, brand, confidence, accept_threshold, verifier
):
    """Apply successful search result and log."""
    match_name = ai_result["record"]["product_name_en"]
    ai_result["_component_reason"] = acceptance_reason
    _apply_search_result(results, row.name, ai_result)
    if trace and trace.enabled:
        trace.log_ai_search_result(
            code, drug_name, norm, brand,
            True, match_name, confidence,
            model_used=ai_result.get("model_used", ""),
            api_failures=verifier.get_fallback_log(),
            accept_threshold=accept_threshold,
            row_index=row.name,
            parse_failed=ai_result.get("parse_failed", False),
        )
    return 1


__all__ = [
    "_try_search_one",
    "_execute_search_and_apply",
    "_apply_successful_search",
]
