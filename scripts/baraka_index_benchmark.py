"""Measure one Excel-target index build and a bounded replay offline."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.core.config.config import load_config
from src.core.excel_target.excel_target_loader import load_target_catalog_from_excel
from src.core.excel_target.excel_target_matching import ExcelTargetMatcher
from src.core.ordering.prevented_items import (
    filter_prevented_order_items,
    load_prevented_items,
)
from src.core.utils.excel import load_match_only_items_from_excel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("state/config.yaml"))
    parser.add_argument("--excel", type=Path, required=True)
    parser.add_argument("--target-key", required=True)
    parser.add_argument("--target-path", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--prevented-items-excel", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    app_config = load_config(args.config)
    target_config = app_config.enabled_excel_targets().get(args.target_key)
    if target_config is None:
        raise SystemExit(f"Unknown or disabled Excel target: {args.target_key}")
    catalog = load_target_catalog_from_excel(
        args.target_path, target_config, source_file=args.target_path.name
    )
    read_limit = 0 if args.prevented_items_excel else max(args.limit, 0)
    items = load_match_only_items_from_excel(args.excel, app_config.excel, limit=read_limit)
    if args.prevented_items_excel:
        items = filter_prevented_order_items(
            items, load_prevented_items(args.prevented_items_excel)
        )
    items = list(itertools.islice(items, args.limit)) if args.limit > 0 else list(items)

    build_started = time.perf_counter()
    matcher = ExcelTargetMatcher(args.target_key, catalog)
    build_ms = (time.perf_counter() - build_started) * 1000
    match_started = time.perf_counter()
    decisions = [matcher.match(item, app_config.matching) for item in items]
    match_ms = (time.perf_counter() - match_started) * 1000
    result = {
        "target_key": args.target_key,
        "catalog_size": len(catalog),
        "item_count": len(items),
        "index_build_ms": round(build_ms, 2),
        "match_total_ms": round(match_ms, 2),
        "match_avg_ms": round(match_ms / len(items), 2) if items else 0.0,
        "matched": sum(decision.decision.best_match is not None for decision in decisions),
        "under_300_seconds": build_ms + match_ms < 300_000,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
