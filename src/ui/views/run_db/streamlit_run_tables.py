"""Item and store drill-down tables for the Run Results (database) tab."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ....core.database.order_runs_read import fetch_item_stores

STATUS_LABELS = {
    "added-to-cart": "🛒 added",
    "matched-only": "🔍 matched",
    "no-results": "⛔ no results",
    "not-orderable": "🚫 not orderable",
    "manual-review": "⚠️ review",
}

SOURCE_LABELS = {
    "tawreed": "👤 Tawreed",
    "excel-target": "📊 Excel target",
}


def render_run_items_table(items: list[dict[str, Any]], *, caption: str = "items") -> None:
    """Render the per-item fact table with friendly status labels."""
    st.markdown(f"**{caption.capitalize()}**")
    frame = pd.DataFrame(items)
    if frame.empty:
        st.info(f"No {caption} stored for this run.")
        return
    frame["status"] = frame["status"].map(
        lambda s: STATUS_LABELS.get(s, s)
    )
    frame["matched"] = frame["matched"].map(_check_mark)
    frame["manual_review_required"] = frame["manual_review_required"].map(
        _check_mark
    )
    if "source_kind" in frame.columns:
        frame["source_kind"] = frame["source_kind"].map(
            lambda kind: SOURCE_LABELS.get(kind, kind) if kind else "—"
        )
    if "source_label" in frame.columns:
        frame["source_label"] = frame["source_label"].map(
            lambda label: label if label else "—"
        )
    st.dataframe(frame, use_container_width=True, hide_index=True)


def render_item_stores_expander(items: list[dict[str, Any]], run_key: str) -> None:
    """Render one expander per unique item revealing its offering-store snapshot.

    ``items`` carries one row per ``(item_key, source_kind, source_label)``
    so a Tawreed + Excel target shared run produces duplicate ``item_key``
    entries. The expander dedupes by ``item_key`` and shows the combined
    snapshot from ``run_item_stores`` (which already aggregates both
    sources) underneath. The store count shown next to each item name
    is the actual row count in ``run_item_stores`` for that item, not
    the per-source ``run_items.stores_offering`` field, because the
    latter only counts one source.
    """
    seen: set[str] = set()
    unique_items: list[dict[str, Any]] = []
    for item in items:
        key = item.get("item_key")
        if not key or key in seen:
            continue
        if not item.get("stores_offering"):
            continue
        seen.add(key)
        unique_items.append(item)
    if not unique_items:
        st.info("No offering-store snapshots stored for this run.")
        return
    st.markdown("**Offering stores per item**")
    for item in unique_items:
        snapshot_rows = fetch_item_stores(run_key, item["item_key"])
        store_count = len(snapshot_rows) if snapshot_rows else 0
        if store_count == 0 and item.get("stores_offering"):
            # Fall back to the per-source count when the snapshot was
            # pruned (e.g. older runs) so the label still shows a
            # non-zero number that matches what the user can see.
            store_count = int(item["stores_offering"])
        label = (
            f"{item['item_name'] or item['item_code']} — "
            f"{store_count} store(s)"
        )
        with st.expander(label):
            _render_store_table(run_key, item["item_key"])


STORE_SOURCE_LABELS = {
    "store_details": "👤 Tawreed",
    "search": "👤 Tawreed",
    "excel_target": "📊 Excel target",
    "excel-target": "📊 Excel target",
}


def _render_store_table(run_key: str, item_key: str) -> None:
    """Fetch and render one item's store rows, winner first."""
    stores = fetch_item_stores(run_key, item_key)
    if not stores:
        st.caption("Snapshot rows were pruned for this item.")
        return
    frame = pd.DataFrame(stores)
    frame["is_winner"] = frame["is_winner"].map(_check_mark)
    if "source" in frame.columns:
        frame["source"] = frame["source"].map(
            lambda value: STORE_SOURCE_LABELS.get(value, value) if value else "—"
        )
    _annotate_price_columns(frame)
    st.dataframe(frame, use_container_width=True, hide_index=True)


def _annotate_price_columns(frame: pd.DataFrame) -> None:
    """Append a ``price_note`` column so users never confuse retail vs purchase.

    Tawreed rows expose both ``purchase_price`` (what the pharmacy pays)
    and ``public_price`` (what the pharmacy charges end customers).
    Excel target rows only have ``public_price`` because the catalog
    carries retail prices — the missing ``purchase_price`` is therefore
    expected, not a data error.

    The note column makes that semantic explicit so the operator can
    tell the two sources apart at a glance without reading the schema.
    """
    if "source" not in frame.columns:
        return
    is_excel = (
        frame["source"].astype(str).str.contains("excel", case=False, na=False)
    )
    notes = ["💵 purchase price" for _ in range(len(frame))]
    for idx, excel_row in enumerate(is_excel):
        if excel_row:
            notes[idx] = "💰 retail (reference)"
    frame["price_note"] = notes


def _check_mark(value: Any) -> str:
    """Render 0/1 sqlite flags as unicode check/cross marks."""
    return "✅" if value else "—"
