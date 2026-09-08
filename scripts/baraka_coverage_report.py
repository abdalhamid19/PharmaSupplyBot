"""Write an offline identity/variant coverage report for one Excel target."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.core.config.config import load_config
from src.core.excel_target.coverage import build_coverage_records
from src.core.excel_target.excel_target_loader import load_target_catalog_from_excel
from src.core.excel_target.excel_target_matching import ExcelTargetMatcher
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


def _write_report(prefix: Path, records) -> None:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    rows = [record.to_row() for record in records]
    fieldnames = list(rows[0]) if rows else [
        "target_key",
        "source_file",
        "item_code",
        "item_name",
        "catalog_size",
        "candidate_count",
        "compatible_count",
        "identity_evidence_kind",
        "identity_evidence",
        "compatibility_status",
        "compatibility_rejection",
        "coverage_category",
        "candidate_codes",
    ]
    with prefix.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with prefix.with_suffix(".jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


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
    matcher = ExcelTargetMatcher(args.target_key, catalog)
    records = build_coverage_records(
        matcher, _load_items(args, app_config), app_config.matching
    )
    _write_report(args.output_prefix, records)
    categories = Counter(record.coverage_category for record in records)
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
