"""Item and store drill-down tables for the Run Results (database) tab."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ....core.database.order_runs_read import fetch_item_stores
from ....core.pricing import PROVENANCE_LABELS

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
    _render_pricing_help_banner(run_key)
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

EXCEL_PROVENANCE_PREFIX = "excel_"

PRICING_HELP_TEXT = (
    "💡 **Public** = price the warehouse charges end customers. "
    "**Purchase** = price the pharmacy actually pays. "
    "**Net** = purchase after the discount. "
    "For Excel targets the file lists only the public price; "
    "the purchase price is derived as `public × (1 − discount%)`."
)

EXCEL_RUN_CAPTION = (
    "📊 This run includes Excel-target stores. Their public and purchase "
    "prices are identical by definition — only the net price (after "
    "discount) and the discount % vary."
)


def _render_pricing_help_banner(run_key: str) -> None:
    """Show the pricing help text and the Excel-specific caption when relevant."""
    st.caption(PRICING_HELP_TEXT)
    try:
        any_excel = _run_has_excel_rows(run_key)
    except Exception:
        any_excel = False
    if any_excel:
        st.caption(EXCEL_RUN_CAPTION)


def _run_has_excel_rows(run_key: str) -> bool:
    """Return whether any ``run_item_stores`` row for the run is from Excel."""
    from ....core.database.order_runs_read import order_runs_connection

    sql = (
        "select 1 from run_item_stores where run_key = ? and source = "
        "'excel_target' limit 1"
    )
    rows = order_runs_connection(None).execute_query(sql, (run_key,))
    return bool(rows)


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
    frame = _enrich_pricing_columns(frame)
    st.dataframe(frame, use_container_width=True, hide_index=True)


def _enrich_pricing_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Add ``Net price``, ``Margin %`` and ``Provenance`` columns when useful."""
    if frame.empty:
        return frame
    if {"public_price", "purchase_price"}.issubset(frame.columns):
        public = pd.to_numeric(frame["public_price"], errors="coerce")
        purchase = pd.to_numeric(frame["purchase_price"], errors="coerce")
        discount = pd.to_numeric(frame.get("discount_percent"), errors="coerce")
        rate = (1.0 - discount.fillna(0.0) / 100.0).clip(lower=0.0)
        net = purchase.where(purchase.notna(), public).mul(rate)
        frame["net_price"] = net.round(2)
        margin = (public - purchase) / public.replace({0: pd.NA})
        frame["margin_percent"] = margin.mul(100).round(2)
    if "price_provenance" in frame.columns:
        frame["provenance"] = frame["price_provenance"].map(
            lambda v: PROVENANCE_LABELS.get(v, v or "—")
        )
    return frame


def _check_mark(value: Any) -> str:
    """Render 0/1 sqlite flags as unicode check/cross marks."""
    return "✅" if value else "—"