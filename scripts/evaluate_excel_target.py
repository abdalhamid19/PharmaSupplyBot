"""Compare offline Excel-target coverage reports without touching runtime state."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


DEFAULT_GOLD_LABELS = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "core"
    / "excel_target"
    / "fixtures"
    / "gold_labels.csv"
)


def evaluate_reports(
    before_path: Path,
    after_path: Path,
    *,
    gold_path: Path | None = DEFAULT_GOLD_LABELS,
) -> dict[str, object]:
    """Compare two coverage CSV files and return a deterministic report."""
    before_rows = _read_rows(before_path)
    after_rows = _read_rows(after_path)
    before_by_key = _index_rows(before_rows)
    after_by_key = _index_rows(after_rows)
    new_reviews = _changed_review_keys(before_by_key, after_by_key, became=True)
    removed_reviews = _changed_review_keys(before_by_key, after_by_key, became=False)
    report = _comparison_report(
        before_rows, after_rows, new_reviews, removed_reviews
    )
    report.update(
        {
            "safety_errors": _safety_errors(after_rows),
            "gold_validation": _validate_gold(after_by_key, gold_path),
            "data_quality_errors": _data_quality_errors(after_rows),
        }
    )
    return report


def _comparison_report(before_rows, after_rows, new_reviews, removed_reviews):
    return {
        "before": _summary(before_rows),
        "after": _summary(after_rows),
        "matched_set_before": _matched_set(before_rows),
        "matched_set_after": _matched_set(after_rows),
        "new_review_items": [list(key) for key in new_reviews],
        "removed_review_items": [list(key) for key in removed_reviews],
        "candidate_categories": _candidate_categories(after_rows),
        "candidate_labels": _candidate_labels(after_rows, new_reviews),
    }


def _read_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _index_rows(rows: Iterable[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    indexed: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = _item_key(row)
        if key in indexed:
            raise ValueError(f"duplicate evaluator row key: {key!r}")
        indexed[key] = row
    return indexed


def _item_key(row: dict[str, str]) -> tuple[str, str]:
    return (str(row.get("item_code", "")), str(row.get("item_name", "")))


def _matched_set(rows: Iterable[dict[str, str]]) -> list[list[str]]:
    matches = []
    for row in rows:
        if _is_matched(row):
            matches.append([*_item_key(row), _matched_product_id(row)])
    return sorted(matches)


def _is_matched(row: dict[str, str]) -> bool:
    return str(row.get("status", "")).casefold() in {"matched", "matched-only"}


def _matched_product_id(row: dict[str, str]) -> str:
    return str(
        row.get("matched_store_product_id")
        or row.get("store_product_id")
        or ""
    )


def _is_reviewable(row: dict[str, str]) -> bool:
    explicit = str(row.get("manual_review_required", "")).casefold()
    if "manual_review_required" in row and explicit:
        return explicit in {"true", "1", "yes"}
    return _candidate_count(row) > 0


def _candidate_count(row: dict[str, str]) -> int:
    raw = row.get(
        "candidate_count_total",
        row.get("review_candidate_count_total", row.get("candidate_count", "0")),
    )
    try:
        return max(0, int(float(raw or 0)))
    except (TypeError, ValueError):
        raise ValueError(f"invalid candidate count in evaluator row: {raw!r}")


def _saved_candidate_count(row: dict[str, str]) -> int:
    field = (
        "candidate_count"
        if "candidate_count_total" in row
        else "review_candidate_count_saved"
    )
    raw = row.get(field, "0")
    try:
        return max(0, int(float(raw or 0)))
    except (TypeError, ValueError):
        raise ValueError(f"invalid saved candidate count in evaluator row: {raw!r}")


def _data_quality_errors(rows: Iterable[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for row in rows:
        total = _candidate_count(row)
        saved = _saved_candidate_count(row)
        if saved > total:
            errors.append(f"saved candidates exceed total: {_item_key(row)!r}")
        if (
            str(row.get("manual_review_required", "")).casefold()
            in {"true", "1", "yes"}
            and total == 0
        ):
            errors.append(f"manual review without candidate: {_item_key(row)!r}")
    return sorted(set(errors))


def _changed_review_keys(before, after, *, became: bool) -> list[tuple[str, str]]:
    keys = sorted(set(before) | set(after))
    changed = []
    for key in keys:
        before_state = _is_reviewable(before.get(key, {}))
        after_state = _is_reviewable(after.get(key, {}))
        is_changed = (
            (not before_state and after_state)
            if became
            else (before_state and not after_state)
        )
        if is_changed:
            changed.append(key)
    return changed


def _summary(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    rows = list(rows)
    return {
        "processed": len(rows),
        "matched": sum(_is_matched(row) for row in rows),
        "manual_review": sum(_is_reviewable(row) for row in rows),
        "identity_absent": sum(
            _coverage_category(row) == "identity_absent" for row in rows
        ),
        "identity_variant_rejected": sum(
            _coverage_category(row) == "identity_variant_rejected"
            for row in rows
        ),
        "excel_target_candidate_available": sum(
            _coverage_category(row) == "excel_target_candidate_available"
            for row in rows
        ),
    }


def _candidate_categories(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    counts = Counter(
        _coverage_category(row) for row in rows if _is_reviewable(row)
    )
    return dict(sorted(counts.items()))


def _coverage_category(row: dict[str, str]) -> str:
    """Read the normalized category from either evaluator or CLI artifacts."""
    return str(row.get("coverage_category") or row.get("manual_review_category") or "")


def _candidate_labels(rows, new_keys: Iterable[tuple[str, str]]) -> list[dict[str, object]]:
    indexed = _index_rows(rows)
    labels: list[dict[str, object]] = []
    for key in new_keys:
        row = indexed[key]
        codes = [code for code in row.get("candidate_codes", "").split(";") if code]
        labels.append(
            {
                "item_code": key[0],
                "item_name": key[1],
                "candidate_codes": codes,
                "label": row.get("candidate_label", "unlabeled"),
            }
        )
    return labels


def _safety_errors(rows: Iterable[dict[str, str]]) -> list[str]:
    errors = [
        error
        for row in rows
        for error in _row_safety_errors(row)
    ]
    return sorted(set(errors))


def _row_safety_errors(row: dict[str, str]) -> list[str]:
    if not _is_matched(row):
        return []
    evidence = row.get("identity_evidence_kind", "")
    status = row.get("compatibility_status", "")
    approved_override = (
        "manual_review_rebound" in evidence and status == "approved_manual_override"
    )
    errors = _identity_safety_errors(row, evidence, approved_override)
    if status == "rejected" and not approved_override:
        errors.append(f"rejected compatibility auto-matched: {_item_key(row)!r}")
    if "tawreed" in _source_text(row):
        errors.append(f"non-target source candidate: {_item_key(row)!r}")
    return errors


def _identity_safety_errors(row, evidence: str, approved_override: bool) -> list[str]:
    if approved_override:
        return []
    errors = []
    if "review_fuzzy" in evidence:
        errors.append(f"review_fuzzy auto-matched: {_item_key(row)!r}")
    if "cohere_translation" in evidence:
        errors.append(f"Cohere auto-matched: {_item_key(row)!r}")
    return errors


def _source_text(row: dict[str, str]) -> str:
    return " ".join(
        row.get(field, "") for field in ("matching_source", "source_file")
    ).casefold()


def _validate_gold(
    actual_rows: dict[tuple[str, str], dict[str, str]],
    gold_path: Path | None,
) -> dict[str, object]:
    if gold_path is None:
        return {"path": "", "passed": True, "failures": []}
    failures: list[str] = []
    target_keys = {
        str(row.get("target_key") or "") for row in actual_rows.values()
    }
    for label in _read_rows(Path(gold_path)):
        if label.get("target_key") and target_keys:
            if label.get("target_key") not in target_keys:
                continue
        key = _item_key(label)
        row = actual_rows.get(key)
        if row is None:
            failures.append(f"missing gold row: {key!r}")
            continue
        _check_gold_category(label, row, failures)
        _check_gold_product(label, row, failures)
        _check_gold_variant_evidence(label, row, failures)
    return {"path": str(gold_path), "passed": not failures, "failures": failures}


def _check_gold_category(label, row, failures: list[str]) -> None:
    expected = label.get("expected_category", "")
    actual = row.get("coverage_category", "")
    if actual != expected:
        failures.append(f"{_item_key(label)!r}: category {actual!r} != {expected!r}")
    if expected == "excel_target_candidate_available" and _candidate_count(row) == 0:
        failures.append(f"{_item_key(label)!r}: expected a saved candidate")


def _check_gold_product(label, row, failures: list[str]) -> None:
    expected = label.get("expected_store_product_id", "")
    actual = _matched_product_id(row)
    if expected != actual:
        failures.append(f"{_item_key(label)!r}: product {actual!r} != {expected!r}")


def _check_gold_variant_evidence(label, row, failures: list[str]) -> None:
    name = label.get("item_name", "").casefold()
    required = {
        "concentration": ("strength", "concentration"),
        "form": ("form",),
        "pack": ("pack",),
    }
    for marker, needles in required.items():
        if marker in name and not any(
            needle in row.get("compatibility_rejection", "").casefold()
            for needle in needles
        ):
            failures.append(f"{_item_key(label)!r}: missing {marker} conflict evidence")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD_LABELS)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = evaluate_reports(args.before, args.after, gold_path=args.gold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
