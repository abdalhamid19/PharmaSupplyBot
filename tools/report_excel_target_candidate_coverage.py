"""Report read-only Excel-target candidate coverage metrics.

The tool consumes completed Excel-target artifacts only.  It does not load the
application configuration, open SQLite for writing, or touch input workbooks.
Use it to compare candidate-universe coverage with the candidates that were
actually persisted in the review artifact.

Examples:

    python tools/report_excel_target_candidate_coverage.py \
        --artifact-dir artifacts/excel-target/البركة شركات/20260910_1243 \
        --artifact-dir artifacts/excel-target/القيصر شركات/20260910_1243

An optional labels CSV can contain ``item_key``, ``excel_target_row_key`` and
``label`` columns.  It also accepts the gold-set columns ``item_code``,
``item_name`` and ``expected_row_key``.  Labels are deliberately optional:
without them the tool reports coverage and candidate volume but does not invent
a precision claim.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


IDENTITY_METHODS = {
    "tawreed_dictionary",
    "review_identity",
    "review_identity_prefix",
    "arabic_identity",
    "english_identity",
}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value or default)))
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes"}


def _percent(numerator: int, denominator: int) -> float | None:
    if not denominator:
        return None
    return round(100.0 * numerator / denominator, 4)


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * weight)


def _distribution(values: Iterable[int]) -> dict[str, int | float | None]:
    values = list(values)
    return {
        "count": len(values),
        "mean": round(statistics.mean(values), 4) if values else None,
        "p50": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
        "max": max(values) if values else None,
    }


def _first_file(artifact_dir: Path, pattern: str) -> Path | None:
    files = sorted(
        path for path in artifact_dir.glob(pattern)
        if path.is_file() and not path.name.endswith(".tmp")
    )
    return files[0] if files else None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists() or path.stat().st_size == 0:
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"expected object at {path}:{line_number}")
            records.append(record)
    return records


def _method(option: dict[str, Any]) -> str:
    return str(
        option.get("candidate_method")
        or option.get("identity_evidence_kind")
        or "unknown"
    )


def _is_identity_method(method: str) -> bool:
    return method in IDENTITY_METHODS


def _label_value(raw_label: str) -> str:
    """Normalize reviewed labels to P, N, U, or E without guessing positives."""
    label = raw_label.strip().casefold()
    if label in {"1", "true", "yes", "correct", "positive", "p"}:
        return "P"
    if label in {"0", "false", "no", "negative", "n", "n_variant", "n_prefix"}:
        return "N"
    if label in {"e", "e_stale", "stale"}:
        return "E"
    return "U"


def _label_item_key(row: dict[str, str]) -> str:
    """Return an item key from either artifact-label or gold-set columns."""
    explicit = str(row.get("item_key") or "").strip()
    if explicit:
        return _canonical_item_key(explicit)
    code = str(row.get("item_code") or "").strip()
    name = str(row.get("item_name") or "").strip()
    return _canonical_item_key(f"{code}::{name}") if code and name else ""


def _canonical_item_key(item_key: str) -> str:
    """Make English case differences harmless while preserving Arabic text."""
    return str(item_key or "").strip().casefold()


def _load_labels(path: Path | None) -> dict[tuple[str, str], str]:
    if path is None:
        return {}
    labels: dict[tuple[str, str], str] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            item_key = _label_item_key(row)
            row_key = str(
                row.get("excel_target_row_key")
                or row.get("row_key")
                or row.get("expected_row_key")
                or ""
            ).strip()
            if not item_key or not row_key:
                continue
            label = str(row.get("label") or row.get("correct") or "")
            labels[(item_key, row_key)] = _label_value(label)
    return labels


def _precision_sample(
    records: list[dict[str, Any]],
    labels: dict[tuple[str, str], str],
) -> dict[str, Any]:
    if not labels:
        return _empty_precision_sample()
    counts, method_counts, labeled_items, positive_saved, positive_ranks = (
        _collect_precision_stats(records, labels)
    )
    positive_label_items = {
        item_key for (item_key, _), label in labels.items() if label == "P"
    }
    return _precision_metrics(
        counts,
        method_counts,
        labeled_items,
        positive_saved,
        positive_ranks,
        positive_label_items,
    )


def _precision_metrics(
    counts,
    method_counts,
    labeled_items,
    positive_saved,
    positive_ranks,
    positive_label_items,
):
    """Assemble precision and rank-recall metrics from collected labels."""
    labeled_candidates = counts["P"] + counts["N"]
    positive_candidates = counts["P"]
    return {
        **_precision_counts(counts, labeled_items, labeled_candidates, positive_candidates),
        **_precision_recall(
            positive_saved, positive_ranks, positive_label_items
        ),
        "precision_by_candidate_method": _method_precision(method_counts),
    }


def _precision_counts(counts, labeled_items, labeled_candidates, positive_candidates):
    """Return the reviewed candidate counts."""
    return {
        "status": "computed",
        "labeled_items": len(labeled_items),
        "labeled_candidates": labeled_candidates,
        "positive_candidates": positive_candidates,
        "negative_candidates": counts["N"],
        "uncertain_candidates": counts["U"],
        "stale_candidates": counts["E"],
        "precision_percent": _percent(positive_candidates, labeled_candidates),
    }


def _precision_recall(positive_saved, positive_ranks, positive_label_items):
    """Return saved-candidate recall at the supported rank cutoffs."""
    return {
        "positive_label_items": len(positive_label_items),
        "recall_at_saved_percent": _percent(
            len(positive_saved), len(positive_label_items)
        ),
        "recall_at_1_percent": _rank_recall(positive_ranks, positive_label_items, 1),
        "recall_at_3_percent": _rank_recall(positive_ranks, positive_label_items, 3),
        "recall_at_5_percent": _rank_recall(positive_ranks, positive_label_items, 5),
    }


def _empty_precision_sample() -> dict[str, Any]:
    """Return the explicit result for a report without reviewed labels."""
    return {
        "status": "labels_not_provided",
        "labeled_items": 0,
        "labeled_candidates": 0,
        "positive_candidates": 0,
        "precision_percent": None,
        "recall_at_saved_percent": None,
        "recall_at_1_percent": None,
        "recall_at_3_percent": None,
        "recall_at_5_percent": None,
        "precision_by_candidate_method": {},
    }


def _collect_precision_stats(records, labels):
    """Collect reviewed counts and saved positive ranks."""
    counts = Counter()
    method_counts: dict[str, Counter[str]] = {}
    labeled_items: set[str] = set()
    positive_saved: set[str] = set()
    positive_ranks: dict[str, int] = {}
    for item_key, option, label, rank in _labeled_options(records, labels):
        labeled_items.add(item_key)
        counts[label] += 1
        method_counts.setdefault(_method(option), Counter())[label] += 1
        if label == "P":
            positive_saved.add(item_key)
            positive_ranks[item_key] = min(positive_ranks.get(item_key, rank), rank)
    return counts, method_counts, labeled_items, positive_saved, positive_ranks


def _method_precision(method_counts):
    """Calculate labeled precision by candidate method."""
    return {
        method: {
            "positive": values["P"],
            "negative": values["N"],
            "uncertain": values["U"],
            "stale": values["E"],
            "precision_percent": _percent(
                values["P"], values["P"] + values["N"]
            ),
        }
        for method, values in sorted(method_counts.items())
    }


def _labeled_options(records, labels):
    """Yield saved options with their reviewed label and one-based rank."""
    for record in records:
        item_key = _canonical_item_key(record.get("item_key") or "")
        for rank, option in enumerate(record.get("options") or [], start=1):
            if not isinstance(option, dict):
                continue
            row_key = str(option.get("excel_target_row_key") or "")
            label = labels.get((item_key, row_key))
            if label:
                yield item_key, option, label, rank


def _rank_recall(
    positive_ranks: dict[str, int], positive_items: set[str], rank_limit: int
) -> float | None:
    """Return recall for positive labels found at or above a rank limit."""
    hits = sum(
        rank <= rank_limit
        for item_key, rank in positive_ranks.items()
        if item_key in positive_items
    )
    return _percent(hits, len(positive_items))


def report_artifact_dir(
    artifact_dir: Path,
    *,
    labels: dict[tuple[str, str], str] | None = None,
) -> dict[str, Any]:
    """Return metrics for one completed target artifact directory."""
    summary_path = _first_file(artifact_dir, "match_only_summary_*.csv")
    if summary_path is None:
        raise FileNotFoundError(
            f"no completed match_only_summary_*.csv in {artifact_dir}"
        )
    candidate_path = _first_file(
        artifact_dir, "manual_review_candidates_excel-target_*.jsonl"
    )
    summary_rows = _read_csv(summary_path)
    candidate_records = _read_jsonl(candidate_path)
    records_by_item: dict[str, dict[str, Any]] = {}
    for record in candidate_records:
        item_key = str(record.get("item_key") or "").strip()
        if not item_key:
            raise ValueError(f"candidate record without item_key in {candidate_path}")
        if item_key in records_by_item:
            raise ValueError(f"duplicate item_key {item_key!r} in {candidate_path}")
        records_by_item[item_key] = record

    total_counts: list[int] = []
    saved_counts: list[int] = []
    displayed_counts: list[int] = []
    manual_review_items = 0
    candidate_items = 0
    identity_absent_items = 0
    method_counts: Counter[str] = Counter()
    identity_saved = 0
    discovery_saved = 0
    unique_row_keys: set[str] = set()

    for row in summary_rows:
        total = _as_int(row.get("candidate_count_total"))
        item_key = f"{row.get('item_code', '')}::{row.get('item_name', '')}"
        record = records_by_item.get(item_key)
        saved = _as_int(
            (record or {}).get("candidate_count_saved"),
            _as_int(row.get("candidate_count_saved"), _as_int(row.get("candidate_count"))),
        )
        if saved < 0 or saved > total:
            raise ValueError(
                f"invalid candidate counts for {item_key}: saved={saved}, total={total}"
            )
        if record is not None:
            envelope_total = _as_int(record.get("candidate_count_total"), total)
            envelope_saved = _as_int(record.get("candidate_count_saved"), saved)
            option_count = len(record.get("options") or [])
            if envelope_total != total:
                raise ValueError(
                    f"summary/envelope total mismatch for {item_key}: "
                    f"summary={total}, envelope={envelope_total}"
                )
            if envelope_saved != saved or option_count != saved:
                raise ValueError(
                    f"envelope saved/options mismatch for {item_key}: "
                    f"saved={envelope_saved}, options={option_count}"
                )
        total_counts.append(total)
        saved_counts.append(saved)
        if row.get("candidate_count_displayed") not in (None, ""):
            displayed_counts.append(_as_int(row.get("candidate_count_displayed")))
        if total > 0:
            candidate_items += 1
        if _as_bool(row.get("manual_review_required")):
            manual_review_items += 1
        if str(row.get("manual_review_category") or "") == "identity_absent":
            identity_absent_items += 1

    for record in candidate_records:
        for option in record.get("options") or []:
            if not isinstance(option, dict):
                continue
            method = _method(option)
            method_counts[method] += 1
            if _is_identity_method(method):
                identity_saved += 1
            else:
                discovery_saved += 1
            row_key = str(option.get("excel_target_row_key") or "")
            if row_key:
                unique_row_keys.add(row_key)

    labels = labels or {}
    return {
        "artifact_dir": str(artifact_dir),
        "summary_file": str(summary_path),
        "candidate_file": str(candidate_path) if candidate_path else None,
        "items_total": len(summary_rows),
        "candidate_available_items": candidate_items,
        "manual_review_items": manual_review_items,
        "identity_absent_items": identity_absent_items,
        "candidate_coverage_percent": _percent(candidate_items, len(summary_rows)),
        "manual_review_rate_percent": _percent(manual_review_items, len(summary_rows)),
        "candidate_universe_total": sum(total_counts),
        "candidate_generated_total": sum(total_counts),
        "candidate_union_total": sum(total_counts),
        "candidate_saved_total": sum(saved_counts),
        "candidate_displayed_total": (
            sum(displayed_counts) if displayed_counts else None
        ),
        "candidate_identity_saved_total": identity_saved,
        "candidate_discovery_saved_total": discovery_saved,
        "unique_saved_row_keys": len(unique_row_keys),
        "candidate_method_counts_saved": dict(sorted(method_counts.items())),
        "candidate_count_total_distribution": _distribution(total_counts),
        "candidate_count_saved_distribution": _distribution(saved_counts),
        "candidate_count_displayed_distribution": _distribution(displayed_counts),
        "precision_sample": _precision_sample(candidate_records, labels),
    }


def build_report(
    artifact_dirs: list[Path], labels_path: Path | None = None
) -> dict[str, Any]:
    labels = _load_labels(labels_path)
    reports = [report_artifact_dir(path, labels=labels) for path in artifact_dirs]
    return {
        "schema_version": 1,
        "read_only": True,
        "labels_file": str(labels_path) if labels_path else None,
        "reports": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-dir",
        action="append",
        type=Path,
        required=True,
        help="completed Excel-target artifact directory; repeat per target/run",
    )
    parser.add_argument("--labels", type=Path, help="optional reviewed-label CSV")
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    args = parser.parse_args()
    report = build_report(args.artifact_dir, args.labels)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.buffer.write(payload.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
