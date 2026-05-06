"""CSV summary writer for Tawreed match-only runs."""

from __future__ import annotations

from ..core.matching_models import MatchDecision
from ..core.utils.excel import Item
from .tawreed_artifacts import append_csv_artifact
from .tawreed_match_logs import OrderItemSummary
from .tawreed_match_only_rows import match_only_summary_rows

MATCH_ONLY_SUMMARY_LABEL = "match_only_summary"


def append_match_only_summary(
    profile_key: str,
    item: Item,
    summary: OrderItemSummary,
    decision: MatchDecision | None,
    label_suffix: str | None = None,
) -> None:
    """Append match-only summary rows without touching order-result summaries."""
    rows = match_only_summary_rows(item, summary, decision)
    append_csv_artifact(
        profile_key, MATCH_ONLY_SUMMARY_LABEL, rows, label_suffix=label_suffix
    )
