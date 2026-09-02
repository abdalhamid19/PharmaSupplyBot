"""Item and store drill-down tables for the Run Results (database) tab."""

from __future__ import annotations

from typing import Any, Callable

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


def render_run_items_table(
    items: list[dict[str, Any]],
    *,
    caption: str = "items",
    source_label_resolver: Callable[[str, str], str] | None = None,
) -> None:
    """Render the per-item fact table with friendly status labels.

    ``source_label_resolver(kind, key)`` maps the raw ``source_label`` key
    (e.g. ``wardany``) to its configured display name (e.g. ``صيدلية الورداني``).
    When omitted, the raw key is shown.
    """
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
        raw_kind = frame["source_kind"].copy()
        frame["source_kind"] = frame["source_kind"].map(
            lambda kind: SOURCE_LABELS.get(kind, kind) if kind else "—"
        )
        if "source_label" in frame.columns and source_label_resolver is not None:
            frame["source_label"] = [
                _resolve_source_label(raw_kind.iloc[i], frame["source_label"].iloc[i], source_label_resolver)
                for i in range(len(frame))
            ]
    if "source_label" in frame.columns:
        frame["source_label"] = frame["source_label"].map(
            lambda label: label if label else "—"
        )
    st.dataframe(frame, use_container_width=True, hide_index=True)


def _resolve_source_label(
    kind: str, label: str, resolver: Callable[[str, str], str]
) -> str:
    """Resolve a raw ``source_label`` key to a friendly display name."""
    if not label:
        return ""
    resolved = resolver(str(kind or ""), str(label))
    return resolved or label


def render_item_stores_expander(items: list[dict[str, Any]], run_key: str) -> None:
    """Render one expander per item revealing its offering-store snapshot.

    Disabled by default; callers must opt in via ``show_store_details=True``.
    The bulk of the per-item store snapshot lives in ``render_run_items_table``
    via the ``winner_store_key`` and ``stores_offering`` columns, so this
    expander is only useful when a pharmacist wants to inspect every store
    for a single item.
    """
    return None


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
