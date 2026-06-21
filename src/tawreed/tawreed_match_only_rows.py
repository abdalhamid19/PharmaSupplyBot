"""Row builders for Tawreed match-only summary artifacts."""

from __future__ import annotations

from ..core.matching_models import MatchDecision
from ..core.utils.excel import Item
from .tawreed_match_logs import OrderResultSummary
from .tawreed_timing import timing_summary_fields
from .tawreed_match_only_fields import (
    best_match_attr,
    candidate_summary_fields,
    sorted_diagnostics,
)


def match_only_summary_rows(
    item: Item, summary: OrderResultSummary, decision: MatchDecision | None
) -> list[dict[str, object]]:
    """Build one summary row per candidate considered during match-only mode."""
    diagnostics = sorted_diagnostics(decision)
    if not diagnostics:
        return [_base_row(item, summary, decision)]
    return [
        _candidate_row(item, summary, decision, diagnostic, rank)
        for rank, diagnostic in enumerate(diagnostics, start=1)
    ]


def _candidate_row(item, summary, decision, diagnostic, rank) -> dict[str, object]:
    """Return a candidate-level match-only summary row."""
    row = _base_row(item, summary, decision)
    row.update(candidate_summary_fields(decision, diagnostic, rank))
    return row


def _base_row(
    item: Item, summary: OrderResultSummary, decision: MatchDecision | None
) -> dict[str, object]:
    """Return item-level match-only fields shared by every row."""
    return {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "status": summary.status,
        "reason": summary.reason,
        "final_reason": decision.final_reason if decision else "",
        "best_match_query": best_match_attr(decision, "query"),
        "best_match_row_index": best_match_attr(decision, "row_index"),
        "best_match_score": best_match_attr(decision, "score"),
        "matched_query": summary.matched_query,
        "searched_queries_count": summary.searched_queries_count,
        "searched_queries": summary.searched_queries,
        "elapsed_seconds": round(summary.elapsed_seconds, 3),
        "match_elapsed_seconds": round(summary.match_elapsed_seconds, 3),
        **timing_summary_fields(summary.timing_seconds),
    }
