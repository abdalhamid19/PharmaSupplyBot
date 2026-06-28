"""Data models for match logs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderResultSummary:
    """One compact execution summary row for an item processed during ordering."""

    status: str
    reason: str
    ordered_total_qty: int = 0
    matched_product_english_name: str = ""
    matched_product_english_name_source: str = ""
    matched_product_arabic_name: str = ""
    matched_query: str = ""
    selected_discount_percent: str = ""
    selected_store_name: str = ""
    searched_queries_count: int = 0
    searched_queries: str = ""
    elapsed_seconds: float = 0.0
    match_elapsed_seconds: float = 0.0
    timing_seconds: dict[str, float] | None = None


__all__ = ["OrderResultSummary"]
