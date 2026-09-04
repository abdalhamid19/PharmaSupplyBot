"""Build a Missed Discount Opportunities report for a given run.

Usage: python -m scripts.build_missed_discount_report <run_key>
"""
import csv
import sqlite3
import sys
from pathlib import Path


def build_report(db_path: str, run_key: str, out_csv: str) -> int:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    sql = """
    WITH best AS (
        SELECT item_key,
               MAX(discount_percent) AS best_discount,
               MIN(purchase_price)    AS best_price
        FROM run_item_stores
        WHERE run_key = ?
        GROUP BY item_key
    ),
    winners AS (
        SELECT item_key,
               discount_percent AS winner_discount,
               purchase_price    AS winner_price,
               source            AS winner_source,
               store_product_id  AS winner_store_product_id,
               store_key         AS winner_store_key
        FROM run_item_stores
        WHERE run_key = ? AND is_winner = 1
    ),
    best_rows AS (
        SELECT s.item_key, s.store_key, s.store_product_id,
               s.discount_percent, s.purchase_price
        FROM run_item_stores s
        JOIN best b
          ON b.item_key = s.item_key
         AND b.best_discount = s.discount_percent
         AND b.best_price    = s.purchase_price
        WHERE s.run_key = ?
    )
    SELECT
        i.item_code                              AS item_code,
        i.item_name                              AS item_name,
        w.winner_discount                        AS winner_discount,
        b.best_discount                          AS best_discount,
        ROUND(b.best_discount - w.winner_discount, 2) AS missed,
        w.winner_price                           AS winner_price,
        b.best_price                             AS best_price,
        ROUND(COALESCE(b.best_price, 0) - COALESCE(w.winner_price, 0), 2) AS price_diff,
        w.winner_source                          AS winner_source,
        w.winner_store_key                       AS winner_store_key,
        w.winner_store_product_id                AS winner_store_product_id,
        (SELECT store_key        FROM best_rows br WHERE br.item_key = w.item_key LIMIT 1) AS best_store_key,
        (SELECT store_product_id FROM best_rows br WHERE br.item_key = w.item_key LIMIT 1) AS best_store_product_id
    FROM winners w
    JOIN best b ON b.item_key = w.item_key
    JOIN items i ON i.item_key = w.item_key
    WHERE b.best_discount > w.winner_discount + 0.01
    ORDER BY missed DESC, i.item_name
    """
    c.execute(sql, (run_key, run_key, run_key))
    rows = c.fetchall()
    headers = [
        "item_code", "item_name",
        "winner_discount", "best_discount", "missed",
        "winner_price",   "best_price",    "price_diff",
        "winner_source",  "winner_store_key", "winner_store_product_id",
        "best_store_key", "best_store_product_id",
    ]
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    conn.close()
    return len(rows)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: build_missed_discount_report <run_key>")
        raise SystemExit(2)
    run_key = sys.argv[1]
    db_path = "state/order_runs.db"
    out = Path("state/reports") / f"missed_discount_{run_key.replace('/', '_')}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    n = build_report(db_path, run_key, str(out))
    print(f"wrote {out} rows={n}")
