"""Write an offline identity/variant coverage report for one Excel target."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.core.config.config import load_config
from src.core.config.config_models import MatchingConfig
from src.core.excel_target.excel_target_loader import load_target_catalog_from_excel
from src.core.excel_target.excel_target_matching import ExcelTargetMatcher
from src.core.excel_target.excel_target_review_candidates import excel_target_row_key
from src.core.ordering.prevented_items import (
    filter_prevented_order_items,
    load_prevented_items,
)
from src.core.utils.excel import load_match_only_items_from_excel


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("state/config.yaml"))
    parser.add_argument("--excel", type=Path, required=True)
    parser.add_argument("--target-key", required=True)
    parser.add_argument("--target-path", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--prevented-items-excel", type=Path)
    parser.add_argument(
        "--output-prefix",
        type=Path,
        required=True,
        help="Path prefix; writes <prefix>.csv and <prefix>.jsonl",
    )
    return parser.parse_args()


def _load_items(args: argparse.Namespace, app_config) -> list:
    prevented_path = args.prevented_items_excel
    read_limit = 0 if prevented_path else max(0, args.limit)
    items = load_match_only_items_from_excel(
        args.excel, app_config.excel, limit=read_limit
    )
    if prevented_path:
        items = filter_prevented_order_items(
            items, load_prevented_items(prevented_path)
        )
    if args.limit > 0:
        items = itertools.islice(items, args.limit)
    return list(items)


def build_enriched_coverage_rows(
    matcher: ExcelTargetMatcher,
    items: Iterable,
    config: MatchingConfig,
) -> list[dict[str, object]]:
    """Build replay rows from the public matcher result seam.

    The legacy coverage module reports identity rows only. This report needs
    both identity coverage and review-only candidates, so it observes the
    matcher's public ``match`` result once per item and records both counts.
    """
    return [_enriched_coverage_row(matcher, item, config) for item in items]


def build_coverage_matcher(target_key: str, catalog, approved_aliases=()) -> ExcelTargetMatcher:
    """Build a replay matcher without reading or writing saved approvals.

    Coverage is a counterfactual diagnostic.  It must describe what the
    current catalog would do on its own, rather than inheriting a historical
    user decision or calling the live translation provider.
    """
    return ExcelTargetMatcher(
        target_key,
        catalog,
        allow_live_translation=False,
        use_saved_approvals=False,
        approved_aliases=approved_aliases,
    )


def _enriched_coverage_row(matcher, item, config) -> dict[str, object]:
    match = matcher.match(item, config)
    identified = tuple(matcher.identity_index.identify(item.name))
    review_candidates = tuple(match.review_candidates)
    best = match.decision.best_match
    category = _coverage_category(best, identified, review_candidates)
    row = {
        "target_key": matcher.target_key,
        "source_file": _source_files(best, identified, review_candidates),
        "item_code": str(item.code or ""),
        "item_name": str(item.name or ""),
        "catalog_size": len(matcher.catalog),
        "candidate_count": len(identified),
        "compatible_count": _compatible_identity_count(item, identified),
        "identity_evidence_kind": _identity_kinds(best, identified),
        "identity_evidence": _identity_details(best, identified),
        "compatibility_status": _compatibility_status(best, review_candidates),
        "compatibility_rejection": _compatibility_rejections(review_candidates),
        "coverage_category": category,
        "status": "matched-only" if best is not None else "no-results",
        "matched_store_product_id": _matched_product_id(best),
        "final_reason": str(match.decision.final_reason or ""),
    }
    row.update(
        _review_candidate_fields(
            matcher.target_key,
            review_candidates,
            config,
            manual_review_required=best is None,
        )
    )
    return row


def _review_candidate_fields(
    target_key,
    candidates,
    config,
    *,
    manual_review_required: bool,
) -> dict[str, object]:
    has_review = manual_review_required and bool(candidates)
    return {
        "candidate_codes": ";".join(
            candidate.product.store_product_id for candidate in candidates
        ),
        "candidate_row_keys": ";".join(
            _candidate_row_key(target_key, candidate) for candidate in candidates
        ),
        "review_candidate_count_total": len(candidates),
        "review_candidate_count_saved": min(len(candidates), _review_save_limit(config)),
        "review_candidate_methods": _candidate_methods(candidates),
        "review_candidate_scores": ";".join(
            f"{float(candidate.score):.2f}" for candidate in candidates
        ),
        "manual_review_required": has_review,
        "manual_review_category": (
            "excel_target_candidate_available" if has_review else ""
        ),
    }


def _candidate_methods(candidates) -> str:
    return ";".join(
        dict.fromkeys(
            method
            for candidate in candidates
            if (method := _candidate_method(candidate))
        )
    )


def _coverage_category(best, identified, review_candidates) -> str:
    if best is not None:
        return "identity_compatible"
    if review_candidates:
        return "excel_target_candidate_available"
    if identified:
        return "identity_variant_rejected"
    return "identity_absent"


def _review_save_limit(config: MatchingConfig) -> int:
    return max(0, int(getattr(config, "manual_review_save_candidate_limit", 0)))


def _compatible_identity_count(item, identified) -> int:
    return sum(
        _candidate_compatibility(item.name, candidate.product.name_ar)
        for candidate in identified
    )


def _candidate_compatibility(query: str, candidate: str) -> int:
    from src.core.excel_target.product_attributes import validate_product_compatibility

    return int(validate_product_compatibility(query, candidate).accepted)


def _identity_kinds(best, identified) -> str:
    if best is not None:
        return str(best.data.get("identity_evidence_kind", ""))
    return ";".join(dict.fromkeys(candidate.evidence.kind for candidate in identified))


def _identity_details(best, identified) -> str:
    if best is not None:
        return str(best.data.get("identity_evidence", ""))
    return "; ".join(dict.fromkeys(candidate.evidence.detail for candidate in identified))


def _compatibility_status(best, review_candidates) -> str:
    if best is not None:
        return str(best.data.get("compatibility_status", ""))
    statuses = {
        str(getattr(candidate, "compatibility_status", "unknown") or "unknown")
        for candidate in review_candidates
    }
    if "compatible" in statuses:
        return "compatible"
    if "rejected" in statuses:
        return "rejected"
    return "unknown"


def _compatibility_rejections(review_candidates) -> str:
    return "; ".join(
        dict.fromkeys(
            str(getattr(candidate, "compatibility_rejection", "") or "")
            for candidate in review_candidates
            if getattr(candidate, "compatibility_rejection", "")
        )
    )


def _source_files(best, identified, review_candidates) -> str:
    values: list[str] = []
    if best is not None:
        values.append(str(best.data.get("excelTargetSourceFile", "")))
    values.extend(candidate.product.source_file for candidate in review_candidates)
    values.extend(candidate.product.source_file for candidate in identified)
    return ";".join(dict.fromkeys(value for value in values if value))


def _candidate_method(candidate) -> str:
    return str(
        getattr(candidate, "candidate_method", "")
        or getattr(candidate, "identity_evidence_kind", "")
        or ""
    )


def _candidate_row_key(target_key: str, candidate) -> str:
    return excel_target_row_key(target_key, candidate.product)


def _matched_product_id(best) -> str:
    if best is None:
        return ""
    return str(best.data.get("storeProductId", ""))


def _write_report(prefix: Path, records) -> None:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    rows = [_record_to_row(record) for record in records]
    _write_csv(prefix, rows)
    _write_jsonl(prefix, rows)


def _record_to_row(record) -> dict:
    return record.to_row() if hasattr(record, "to_row") else dict(record)


def _write_csv(prefix: Path, rows: list[dict]) -> None:
    fieldnames = list(rows[0]) if rows else _default_fieldnames()
    with prefix.with_suffix(".csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(prefix: Path, rows: list[dict]) -> None:
    with prefix.with_suffix(".jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _default_fieldnames() -> list[str]:
    return [
        "target_key", "source_file", "item_code", "item_name", "catalog_size",
        "candidate_count", "compatible_count", "identity_evidence_kind",
        "identity_evidence", "compatibility_status", "compatibility_rejection",
        "coverage_category", "candidate_codes", "candidate_row_keys",
        "review_candidate_count_total", "review_candidate_count_saved",
        "review_candidate_methods", "review_candidate_scores",
        "manual_review_required", "manual_review_category", "status",
        "matched_store_product_id", "final_reason",
    ]


def main() -> None:
    args = _parse_args()
    app_config = load_config(args.config)
    try:
        target_config = app_config.enabled_excel_targets()[args.target_key]
    except KeyError as error:
        raise SystemExit(f"Unknown or disabled Excel target: {args.target_key}") from error
    catalog = load_target_catalog_from_excel(
        args.target_path,
        target_config,
        source_file=args.target_path.name,
    )
    matcher = build_coverage_matcher(
        args.target_key, catalog, approved_aliases=target_config.aliases
    )
    records = build_enriched_coverage_rows(
        matcher, _load_items(args, app_config), app_config.matching
    )
    _write_report(args.output_prefix, records)
    categories = Counter(str(record["coverage_category"]) for record in records)
    print(
        json.dumps(
            {
                "target_key": args.target_key,
                "catalog_size": len(catalog),
                "processed": len(records),
                "categories": dict(categories),
                "csv": str(args.output_prefix.with_suffix(".csv")),
                "jsonl": str(args.output_prefix.with_suffix(".jsonl")),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
