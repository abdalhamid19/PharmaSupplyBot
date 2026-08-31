"""Missed-discount panel: the analytics payoff of the store snapshot DB."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ....core.database.order_runs_read import fetch_missed_discounts


def render_missed_discount_panel(run_key: str | None) -> None:
    """Render items where the winner's discount trails the best offering.

    ``run_key=None`` scans every run in history; a key scopes the panel to
    the selected run.
    """
    st.markdown("**Missed discount opportunities**")
    st.caption(
        "Items where the selected (winner) store had a lower discount than "
        "the best available store in the same run."
    )
    rows = fetch_missed_discounts(run_key)
    if not rows:
        st.success("No missed discounts — the winner always had the best rate.")
        return
    frame = pd.DataFrame(rows)
    frame = frame.drop(columns=["run_key", "item_key"], errors="ignore")
    st.dataframe(frame, use_container_width=True, hide_index=True)
    _render_missed_summary(rows)


def _render_missed_summary(rows: list[dict]) -> None:
    """Render one aggregate line under the missed-discount table."""
    missed = [row["missed"] for row in rows if row["missed"] is not None]
    if missed:
        st.metric("Items affected", len(missed), border=True)
