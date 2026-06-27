"""Helper functions for quality metrics computation."""

import csv
from pathlib import Path
from typing import Any


def _read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    """Read all rows from a CSV file into a list of dicts."""
    with csv_path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def _cell(row: dict[str, Any], key: str) -> str:
    """Return a cleaned string value from a CSV row."""
    return str(row.get(key) or "").strip()


def _increment(counter: dict[str, int], key: str) -> None:
    """Increment a counter dict for the given key."""
    counter[key] = counter.get(key, 0) + 1


def _process_row_metrics(row: dict, metrics) -> None:
    """Process a single row and update metrics."""
    status = _cell(row, "status")
    matched = _cell(row, "matched").lower() in {"true", "1", "yes"}
    manual_review = _cell(row, "manual_review_required").lower() in {"true", "1", "yes"}
    deterministic_found = _cell(row, "deterministic_match_found").lower() in {"true", "1", "yes"}

    _increment(metrics.status_counts, status)

    if matched and not manual_review:
        metrics.auto_matched += 1

    _update_manual_review_metrics(row, metrics, manual_review)
    _update_status_metrics(status, metrics)
    
    if deterministic_found:
        metrics.deterministic_matched += 1

    _update_ai_metrics(_cell(row, "ai_status"), metrics)


def _update_manual_review_metrics(row, metrics, manual_review):
    """Update manual review metrics."""
    if manual_review:
        metrics.manual_review_required += 1
        category = _cell(row, "manual_review_category")
        if category:
            _increment(metrics.category_counts, category)


def _update_status_metrics(status: str, metrics) -> None:
    """Update status-specific metrics."""
    if status == "no-results":
        metrics.no_results += 1
    elif status == "matched-but-unavailable":
        metrics.matched_but_unavailable += 1
    elif status == "not-orderable":
        metrics.not_orderable += 1


def _update_ai_metrics(ai_status: str, metrics) -> None:
    """Update AI-specific metrics."""
    if ai_status == "ai_verified":
        metrics.ai_verified += 1
    elif ai_status == "ai_search_accepted":
        metrics.ai_searched += 1
    elif ai_status == "ai_review_rejected":
        metrics.ai_reviewed += 1
    elif ai_status == "ai_rejected":
        metrics.ai_rejected += 1
    elif ai_status == "ai_low_confidence":
        metrics.ai_low_confidence += 1


__all__ = [
    "_read_csv_rows",
    "_cell",
    "_increment",
    "_process_row_metrics",
    "_update_manual_review_metrics",
    "_update_status_metrics",
    "_update_ai_metrics",
]
