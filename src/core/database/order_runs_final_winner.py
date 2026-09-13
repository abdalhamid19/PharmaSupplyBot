"""Reconcile snapshot winners with the final cross-source purchase decision."""

from __future__ import annotations


def reconcile_final_winner(conn, run_key: str, item_key: str) -> None:
    """Make the chosen Excel offer the only winner for a deferred item.

    A Tawreed store can be selected provisionally while its offers are being
    inspected. Once the shared price rule defers the item to Excel Target, that
    provisional choice must no longer be exposed as the final winner.
    """
    if not _is_deferred_to_excel(conn, run_key, item_key):
        return
    excel_product_id = _lowest_excel_product_id(conn, run_key, item_key)
    if excel_product_id is None:
        return
    _mark_excel_as_only_winner(conn, run_key, item_key, excel_product_id)


def _is_deferred_to_excel(conn, run_key: str, item_key: str) -> bool:
    row = conn.execute(
        "select 1 from run_items where run_key=? and item_key=? "
        "and source_kind='tawreed' and status='deferred-to-excel-target'",
        (run_key, item_key),
    ).fetchone()
    return row is not None


def _lowest_excel_product_id(conn, run_key: str, item_key: str) -> str | None:
    row = conn.execute(
        "select ris.store_product_id from run_item_stores ris "
        "join runs r on r.run_key=ris.run_key "
        "where ris.run_key=? and ris.item_key=? "
        "and ris.source in ('excel_target', 'excel-target') "
        "and ris.available_qty > 0 "
        "and ris.purchase_price > 0 and ris.purchase_price < 1e308 "
        "and coalesce(ris.discount_percent, 0) >= coalesce(r.min_discount_pct, 0) - 0.001 "
        "order by ris.purchase_price, ris.source_label, ris.store_product_id limit 1",
        (run_key, item_key),
    ).fetchone()
    return str(row[0]) if row else None


def _mark_excel_as_only_winner(
    conn, run_key: str, item_key: str, excel_product_id: str
) -> None:
    conn.execute(
        "update run_item_stores set is_winner=0 where run_key=? and item_key=?",
        (run_key, item_key),
    )
    conn.execute(
        "update run_item_stores set is_winner=1 where run_key=? and item_key=? "
        "and store_product_id=? and source in ('excel_target', 'excel-target')",
        (run_key, item_key, excel_product_id),
    )


def backfill_final_winners(conn) -> None:
    """Bring historical deferred items in line with the final-winner rule."""
    tables = {
        row[0]
        for row in conn.execute(
            "select name from sqlite_master where type='table'"
        ).fetchall()
    }
    if "run_items" not in tables or "run_item_stores" not in tables:
        return
    rows = conn.execute(
        "select run_key, item_key from run_items where source_kind='tawreed' "
        "and status='deferred-to-excel-target'"
    ).fetchall()
    for run_key, item_key in rows:
        reconcile_final_winner(conn, run_key, item_key)


__all__ = ["backfill_final_winners", "reconcile_final_winner"]
