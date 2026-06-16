"""Quality metrics for order matching runs.

Reads the order_item_summary CSV produced by each run and computes
acceptance rate, manual-review breakdown, and category-level counts.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunQualityMetrics:
    """Aggregate quality numbers for one order matching run."""

    total_items: int = 0
    auto_matched: int = 0
    manual_review_required: int = 0
    no_results: int = 0
    matched_but_unavailable: int = 0
    not_orderable: int = 0
    ai_verified: int = 0
    ai_searched: int = 0
    ai_reviewed: int = 0
    ai_rejected: int = 0
    ai_low_confidence: int = 0
    deterministic_matched: int = 0
    category_counts: dict[str, int] = field(default_factory=dict)
    status_counts: dict[str, int] = field(default_factory=dict)

    @property
    def auto_match_rate(self) -> float:
        """Return the percentage of items automatically matched."""
        if self.total_items == 0:
            return 0.0
        return round(self.auto_matched / self.total_items * 100, 1)

    @property
    def manual_review_rate(self) -> float:
        """Return the percentage of items requiring manual review."""
        if self.total_items == 0:
            return 0.0
        return round(self.manual_review_required / self.total_items * 100, 1)

    @property
    def no_results_rate(self) -> float:
        """Return the percentage of items with no search results."""
        if self.total_items == 0:
            return 0.0
        return round(self.no_results / self.total_items * 100, 1)

    def format_report(self) -> str:
        """Return a human-readable quality report string."""
        lines = [
            "=" * 60,
            "ORDER MATCHING QUALITY REPORT",
            "=" * 60,
            "",
            f"Total items:                {self.total_items}",
            f"Auto-matched:               {self.auto_matched} ({self.auto_match_rate}%)",
            f"Manual review required:     {self.manual_review_required} ({self.manual_review_rate}%)",
            f"No results:                 {self.no_results} ({self.no_results_rate}%)",
            f"Matched but unavailable:    {self.matched_but_unavailable}",
            f"Not orderable:              {self.not_orderable}",
            "",
            "--- AI Decision Breakdown ---",
            f"Deterministic matched:      {self.deterministic_matched}",
            f"AI verified:                {self.ai_verified}",
            f"AI search accepted:         {self.ai_searched}",
            f"AI reviewed:                {self.ai_reviewed}",
            f"AI rejected:                {self.ai_rejected}",
            f"AI low confidence:          {self.ai_low_confidence}",
            "",
        ]

        if self.status_counts:
            lines.append("--- Status Distribution ---")
            for status, count in sorted(self.status_counts.items(), key=lambda pair: -pair[1]):
                lines.append(f"  {status:<35s} {count}")
            lines.append("")

        if self.category_counts:
            lines.append("--- Manual Review Categories ---")
            for category, count in sorted(self.category_counts.items(), key=lambda pair: -pair[1]):
                lines.append(f"  {category:<35s} {count}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


def compute_quality_metrics(summary_csv_path: Path) -> RunQualityMetrics:
    """Parse an order_item_summary CSV and return computed quality metrics."""
    metrics = RunQualityMetrics()
    rows = _read_csv_rows(summary_csv_path)

    for row in rows:
        metrics.total_items += 1
        status = _cell(row, "status")
        matched = _cell(row, "matched").lower() in {"true", "1", "yes"}
        manual_review = _cell(row, "manual_review_required").lower() in {"true", "1", "yes"}
        ai_status = _cell(row, "ai_status")
        category = _cell(row, "manual_review_category")
        deterministic_found = _cell(row, "deterministic_match_found").lower() in {"true", "1", "yes"}

        _increment(metrics.status_counts, status)

        if matched and not manual_review:
            metrics.auto_matched += 1

        if manual_review:
            metrics.manual_review_required += 1
            if category:
                _increment(metrics.category_counts, category)

        if status == "no-results":
            metrics.no_results += 1
        elif status == "matched-but-unavailable":
            metrics.matched_but_unavailable += 1
        elif status == "not-orderable":
            metrics.not_orderable += 1

        if deterministic_found:
            metrics.deterministic_matched += 1

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

    return metrics


def compute_quality_metrics_from_directory(run_directory: Path) -> RunQualityMetrics:
    """Find and parse the order_item_summary CSV inside a run directory."""
    summary_files = list(run_directory.glob("order_item_summary_*.csv"))
    if not summary_files:
        raise FileNotFoundError(
            f"No order_item_summary CSV found in {run_directory}"
        )
    return compute_quality_metrics(summary_files[0])


def save_quality_report(run_directory: Path) -> Path:
    """Compute metrics and write a quality_report.txt into the run directory."""
    metrics = compute_quality_metrics_from_directory(run_directory)
    report_path = run_directory / "quality_report.txt"
    report_path.write_text(metrics.format_report(), encoding="utf-8")
    return report_path


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
