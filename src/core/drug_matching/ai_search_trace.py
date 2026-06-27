"""Tracing functions for AI search."""

from .normalizer import parse_drug


def _trace_api_attempts(trace, results, idx, parsed, item):
    """Trace API attempts in trace log."""
    if trace and trace.enabled:
        trace.log_api_attempts(
            results.at[idx, "code"], results.at[idx, "drug_name"],
            parsed.normalized, parsed.brand,
            item.get("_api_attempts", []), row_index=idx,
        )


def _trace_parse_failure(trace, results, idx, parsed, item):
    """Trace parse failure in trace log."""
    if trace and trace.enabled and item.get("parse_failed"):
        trace.log_ai_parse_failure(
            results.at[idx, "code"], results.at[idx, "drug_name"],
            parsed.normalized, parsed.brand,
            item.get("reason", ""),
            model_used=item.get("model_used", ""),
            row_index=idx,
        )


def _trace_skip_all_search(results, trace, reason):
    """Log AI search skip for all unmatched drugs."""
    unmatched = results[
        (results["matched_product_name_en"].isna()) |
        (results["matched_product_name_en"] == "")
    ]
    for idx, row in unmatched.iterrows():
        parsed = parse_drug(row["drug_name"])
        trace.log_ai_skip(
            row["code"], row["drug_name"],
            parsed.normalized, parsed.brand,
            "search", reason, row_index=idx,
        )


def _search_error_code(ai_result, confidence, accept_confidence) -> str:
    """Determine error code for search failure."""
    if not ai_result:
        return "no_ai_result"
    if ai_result.get("error_code"):
        return str(ai_result["error_code"])
    if ai_result.get("parse_failed"):
        return "invalid_json"
    if ai_result.get("best_index", 0) == 0:
        return "best_index_0"
    if confidence < accept_confidence:
        return "confidence_below_threshold"
    return "no_record"


def _trace_search_exception(trace, row, exc):
    """Trace search exception in trace log."""
    if not trace or not trace.enabled:
        return
    drug_name = row["drug_name"]
    parsed = parse_drug(drug_name)
    trace.log_ai_search_result(
        str(row.get("code", "")), drug_name, parsed.normalized, parsed.brand,
        False, None, 0,
        api_failures=f"{type(exc).__name__}: {str(exc)[:180]}",
        accept_threshold=0.75,
        row_index=row.name,
        error_code="ai_search_exception",
    )


__all__ = [
    "_trace_api_attempts",
    "_trace_parse_failure",
    "_trace_skip_all_search",
    "_search_error_code",
    "_trace_search_exception",
]
