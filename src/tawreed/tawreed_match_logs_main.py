"""Main match log functions."""

from __future__ import annotations

from ..core.matching_trace import decision_trace_rows
from ..core.matching_models import MatchDecision
from ..core.utils.excel import Item
from .tawreed_artifacts import (
    append_csv_artifact,
    append_text_artifact,
    append_xlsx_artifact,
    write_text_artifact,
)
from .tawreed_timing import timing_summary_fields
from .tawreed_match_logs_decision import should_write_detailed_match_log
from .tawreed_match_logs_content import match_log_content
from .tawreed_match_logs_helpers import safe_item_label, match_log_section_separator
from .tawreed_match_logs_models import OrderResultSummary


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
    "write_match_log",
    "append_order_result_summary",
]
