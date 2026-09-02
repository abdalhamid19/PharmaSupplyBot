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
    """Render one expander per item revealing its offering-store snapshot."""
    with_rows = [item for item in items if item["stores_offering"]]
    if not with_rows:
        st.info("No offering-store snapshots stored for this run.")
        return
    st.markdown("**Offering stores per item**")
    for item in with_rows:
        label = (
            f"{item['item_name'] or item['item_code']} — "
            f"{item['stores_offering']} store(s)"
        )
        with st.expander(label):
            _render_store_table(run_key, item["item_key"])


def _render_store_table(run_key: str, item_key: str) -> None:
    """Fetch and render one item's store rows, winner first."""
    stores = fetch_item_stores(run_key, item_key)
    if not stores:
        st.caption("Snapshot rows were pruned for this item.")
        return
    frame = pd.DataFrame(stores)
    frame["is_winner"] = frame["is_winner"].map(_check_mark)
    st.dataframe(frame, use_container_width=True, hide_index=True)


def _check_mark(value: Any) -> str:
    """Render 0/1 sqlite flags as unicode check/cross marks."""
    return "✅" if value else "—"
