"""Import manual-review decisions from a CSV backup into local SQLite.

Usage:
    python tools/import_csv_to_sqlite.py docs/old_saved_item.csv
    python tools/import_csv_to_sqlite.py path/to/export.csv --db state/manual_review_decisions.db
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Project root on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.manual_review.manual_review_hints import hint_key
from src.core.manual_review.manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)


def _decision_from_csv_row(row: dict) -> ManualReviewDecision | None:
    code = (row.get("item_code") or "").strip()
    name = (row.get("item_name") or "").strip()
    if not code and not name:
        return None

    decision = (row.get("decision") or row.get("manual_decision") or "").strip()
    approved_raw = (row.get("approved") or "").strip().lower()
    if approved_raw in {"1", "true", "yes"}:
        approved = True
    elif approved_raw in {"0", "false", "no"}:
        approved = False
    else:
        approved = decision in {"approved_match", "auto_matched"}

    if not decision:
        decision = "approved_match" if approved else "not_matching"

    return ManualReviewDecision(
        item_code=code,
        item_name=name,
        approved=approved,
        correct_store_product_id=(row.get("correct_store_product_id") or "").strip(),
        correct_product_name=(row.get("correct_product_name") or "").strip(),
        correct_product_name_ar=(row.get("correct_product_name_ar") or "").strip(),
        correct_query=(row.get("correct_query") or "").strip(),
        run_id=(row.get("run_id") or "csv_import").strip(),
        manual_decision=decision,
    )


def import_csv(csv_path: Path, db_path: Path) -> int:
    """Import rows from csv_path into SQLite at db_path. Returns count imported."""
    store = ManualReviewStore(db_path)
    decisions: list[ManualReviewDecision] = []
    seen: set[tuple[str, str]] = set()

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            decision = _decision_from_csv_row(row)
            if decision is None:
                continue
            key = hint_key(decision.item_code, decision.item_name)
            # Last row wins for duplicates in the same file
            if key in seen:
                decisions = [d for d in decisions if hint_key(d.item_code, d.item_name) != key]
            seen.add(key)
            decisions.append(decision)

    store.upsert_batch(decisions)
    return len(decisions)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import manual-review CSV into local SQLite")
    parser.add_argument(
        "csv_path",
        type=Path,
        nargs="?",
        default=Path("docs/old_saved_item.csv"),
        help="CSV file to import (default: docs/old_saved_item.csv)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_MANUAL_REVIEW_DB,
        help=f"SQLite path (default: {DEFAULT_MANUAL_REVIEW_DB})",
    )
    args = parser.parse_args()

    if not args.csv_path.exists():
        raise SystemExit(f"CSV not found: {args.csv_path}")

    count = import_csv(args.csv_path, args.db)
    store = ManualReviewStore(args.db)
    total = len(store.list_decisions())
    print(f"Imported {count} rows from {args.csv_path}")
    print(f"SQLite database: {args.db}")
    print(f"Total decisions now in DB: {total}")


if __name__ == "__main__":
    main()
