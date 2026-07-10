"""Order-result summary row builders."""

from __future__ import annotations

from src.core.ordering.order_selected_fields import selected_store_discount_fields
from src.core.utils.excel import Item

from .tawreed_match_logs_helpers import OrderResultSummary
from .tawreed_timing import timing_summary_fields


def order_result_summary_row(
    item: Item, summary: OrderResultSummary
) -> dict[str, object]:
    """Return one order-result summary artifact row."""
    row = _order_result_base_fields(item, summary)
    row.update(
        selected_store_discount_fields(
            summary.selected_store_name, summary.selected_discount_percent
        )
    )
    row.update(_order_result_tail_fields(summary))
    return row


def _order_result_base_fields(
    item: Item, summary: OrderResultSummary
) -> dict[str, object]:
    """Return non-selection order-result summary fields."""
    return {
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
    }


def _order_result_tail_fields(summary: OrderResultSummary) -> dict[str, object]:
    """Return query and timing fields for an order-result summary row."""
    return {
        "searched_queries_count": summary.searched_queries_count,
        "searched_queries": summary.searched_queries,
        "elapsed_seconds": round(summary.elapsed_seconds, 3),
        "match_elapsed_seconds": round(summary.match_elapsed_seconds, 3),
        **timing_summary_fields(summary.timing_seconds),
    }


__all__ = ["order_result_summary_row"]
