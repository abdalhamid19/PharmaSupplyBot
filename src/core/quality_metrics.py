"""Quality metrics for order matching runs.

Reads the order_item_summary CSV produced by each run and computes
acceptance rate, manual-review breakdown, and category-level counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .quality_metrics_helpers import (
    _cell,
    _increment,
    _process_row_metrics,
    _read_csv_rows,
)


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
        lines = ["=" * 60, "ORDER MATCHING QUALITY REPORT", "=" * 60, ""]
        lines.extend(self._format_summary_section())
        lines.extend(self._format_ai_section())
        lines.extend(self._format_status_section())
        lines.extend(self._format_category_section())
        lines.append("=" * 60)
        return "\n".join(lines)

    def _format_summary_section(self):
        """Format summary statistics section."""
        return [
            f"Total items:                {self.total_items}",
            f"Auto-matched:               {self.auto_matched} ({self.auto_match_rate}%)",
            f"Manual review required:     {self.manual_review_required} ({self.manual_review_rate}%)",
            f"No results:                 {self.no_results} ({self.no_results_rate}%)",
            f"Matched but unavailable:    {self.matched_but_unavailable}",
            f"Not orderable:              {self.not_orderable}",
            "",
        ]

    def _format_ai_section(self):
        """Format AI decision breakdown section."""
        return [
            "--- AI Decision Breakdown ---",
            f"Deterministic matched:      {self.deterministic_matched}",
            f"AI verified:                {self.ai_verified}",
            f"AI search accepted:         {self.ai_searched}",
            f"AI reviewed:                {self.ai_reviewed}",
            f"AI rejected:                {self.ai_rejected}",
            f"AI low confidence:          {self.ai_low_confidence}",
            "",
        ]

    def _format_status_section(self):
        """Format status distribution section."""
        if not self.status_counts:
            return []
        lines = ["--- Status Distribution ---"]
        for status, count in sorted(self.status_counts.items(), key=lambda p: -p[1]):
            lines.append(f"  {status:<35s} {count}")
        lines.append("")
        return lines

    def _format_category_section(self):
        """Format manual review categories section."""
        if not self.category_counts:
            return []
        lines = ["--- Manual Review Categories ---"]
        for category, count in sorted(self.category_counts.items(), key=lambda p: -p[1]):
            lines.append(f"  {category:<35s} {count}")
        lines.append("")
        return lines


def compute_quality_metrics(summary_csv_path: Path) -> RunQualityMetrics:
    """Parse an order_item_summary CSV and return computed quality metrics."""
    metrics = RunQualityMetrics()
    rows = _read_csv_rows(summary_csv_path)

    for row in rows:
        metrics.total_items += 1
        _process_row_metrics(row, metrics)

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


__all__ = [
    "RunQualityMetrics",
    "compute_quality_metrics",
    "compute_quality_metrics_from_directory",
    "save_quality_report",
]
