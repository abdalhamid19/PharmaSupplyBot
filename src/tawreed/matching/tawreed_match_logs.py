"""Diagnostic log builders for Tawreed product matching - re-exports from split modules."""

from __future__ import annotations

from pathlib import Path

from src.core.matching_types import CandidateMatchDiagnostic, MatchDecision
from src.core.matching.matching_trace import decision_trace_rows
from src.core.utils.excel import Item
from ..artifacts.tawreed_artifacts import (
    append_csv_artifact,
    append_text_artifact,
    append_xlsx_artifact,
    write_text_artifact,
)
from .tawreed_timing import timing_summary_fields

# Constants
MAX_DETAILED_MATCH_CANDIDATES = 25

# Re-export from split modules
from .tawreed_match_logs_helpers import (
    OrderResultSummary,
    candidate_name_fields,
    accepted_product_name,
    safe_item_label,
    match_log_section_separator,
    sorted_diagnostics,
    should_write_detailed_match_log,
    _best_match_diagnostic,
)
from .tawreed_match_logs_content import (
    match_log_content,
    _match_log_header_lines,
    candidate_log_lines,
    _candidate_identity_lines,
    _candidate_score_lines,
)
from .tawreed_match_logs_csv import (
    match_log_csv_rows,
    _match_log_csv_row,
    _shared_csv_fields,
    _item_and_candidate_csv_fields,
    _candidate_csv_fields,
    _best_match_csv_fields,
    _score_csv_fields,
)


# ============================================================================
# Main Match Log Functions
# ============================================================================

def write_match_log(bot, item: Item, decision: MatchDecision) -> None:
    """Write detailed TXT and CSV matching diagnostics for one item."""
    if not should_write_detailed_match_log(decision):
        return
    log_content = match_log_content(item, decision)
    log_label = f"match_log_{safe_item_label(item)}"
    write_text_artifact(bot.profile_key, log_label, log_content)
    append_text_artifact(
        bot.profile_key,
        "match_log_all",
        match_log_section_separator(item) + log_content,
    )
    append_csv_artifact(
        bot.profile_key, "matching_trace", decision_trace_rows(item, decision)
    )


def append_order_result_summary(
    profile_key: str,
    item: Item,
    summary: OrderResultSummary,
    label_suffix: str | None = None,
) -> None:
    """Append one compact order-result summary row to the table artifacts."""
    row = {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "ordered_total_qty": summary.ordered_total_qty,
        "status": summary.status,
        "reason": summary.reason,
        "matched_product_english_name": summary.matched_product_english_name,
        "matched_product_english_name_source": (
            summary.matched_product_english_name_source
        ),
        "matched_product_arabic_name": summary.matched_product_arabic_name,
        "matched_query": summary.matched_query,
        "selected_discount_percent": summary.selected_discount_percent,
        "selected_store_name": summary.selected_store_name,
        "searched_queries_count": summary.searched_queries_count,
        "searched_queries": summary.searched_queries,
        "elapsed_seconds": round(summary.elapsed_seconds, 3),
        "match_elapsed_seconds": round(summary.match_elapsed_seconds, 3),
        **timing_summary_fields(summary.timing_seconds),
    }
    if label_suffix:
        append_csv_artifact(
            profile_key, "order_result_summary", [row], label_suffix=label_suffix
        )
        append_xlsx_artifact(
            profile_key, "order_result_summary", [row], label_suffix=label_suffix
        )
        return
    append_csv_artifact(profile_key, "order_result_summary", [row])
    append_xlsx_artifact(profile_key, "order_result_summary", [row])


__all__ = [
    "MAX_DETAILED_MATCH_CANDIDATES",
    "OrderResultSummary",
    "write_match_log",
    "append_order_result_summary",
    "match_log_content",
    "candidate_log_lines",
    "match_log_csv_rows",
    "candidate_name_fields",
    "accepted_product_name",
    "safe_item_label",
    "match_log_section_separator",
    "sorted_diagnostics",
    "should_write_detailed_match_log",
    "_best_match_diagnostic",
    "_match_log_header_lines",
    "_candidate_identity_lines",
    "_candidate_score_lines",
    "_match_log_csv_row",
    "_shared_csv_fields",
    "_item_and_candidate_csv_fields",
    "_candidate_csv_fields",
    "_best_match_csv_fields",
    "_score_csv_fields",
]
