"""One-time export from CockroachDB Cloud into local SQLite.

Use this when Cockroach credits/RUs are restored so you can pull the full
cloud table into the local SQLite file without losing rows.

Usage:
    python tools/export_cockroach_to_sqlite.py
    python tools/export_cockroach_to_sqlite.py --db state/manual_review_decisions.db
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.manual_review.manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)


def _fetch_cockroach_rows():
    try:
        import psycopg2
    except ImportError as exc:
        raise SystemExit(
            "psycopg2 is required for Cockroach export. "
            "Install with: pip install psycopg2-binary"
        ) from exc

    load_dotenv()
    host = os.getenv("DB_HOST")
    password = os.getenv("DB_PASSWORD", "").strip()
    if not host or not password:
        raise SystemExit(
            "Set DB_HOST and DB_PASSWORD in .env to export from CockroachDB."
        )

    conn = psycopg2.connect(
        host=host,
        port=int(os.getenv("DB_PORT", "26257")),
        database=os.getenv("DB_NAME", "defaultdb"),
        user=os.getenv("DB_USER"),
        password=password,
        sslmode=os.getenv("DB_SSLMODE", "require"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT item_code, item_name, approved, correct_store_product_id,
                       manual_decision, correct_product_name, correct_product_name_ar,
                       correct_query, run_id
                FROM manual_review_decisions
                """
            )
            return cur.fetchall()
    finally:
        conn.close()


def export_to_sqlite(db_path: Path) -> int:
    rows = _fetch_cockroach_rows()
    store = ManualReviewStore(db_path)
    decisions = [
        ManualReviewDecision(
            item_code=str(row[0] or ""),
            item_name=str(row[1] or ""),
            approved=bool(row[2]),
            correct_store_product_id=str(row[3] or ""),
            manual_decision=str(row[4] or ""),
            correct_product_name=str(row[5] or ""),
            correct_product_name_ar=str(row[6] or ""),
            correct_query=str(row[7] or ""),
            run_id=str(row[8] or "cockroach_export"),
        )
        for row in rows
    ]
    store.upsert_batch(decisions)
    return len(decisions)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export manual_review_decisions from CockroachDB to local SQLite"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_MANUAL_REVIEW_DB,
        help=f"Destination SQLite path (default: {DEFAULT_MANUAL_REVIEW_DB})",
    )
    args = parser.parse_args()

    try:
        count = export_to_sqlite(args.db)
    except Exception as error:
        raise SystemExit(
            f"Export failed (cluster may still be disabled for credits): {error}"
        ) from error

    total = len(ManualReviewStore(args.db).list_decisions())
    print(f"Exported {count} rows from CockroachDB into {args.db}")
    print(f"Total decisions now in SQLite: {total}")


if __name__ == "__main__":
    main()
