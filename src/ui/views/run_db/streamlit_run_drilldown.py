"""In-page KPI filter bar for the Run Results (database) tab.

Each KPI card is a toggle button: clicking it makes that category the
``active_kpi_category`` session-state key and reruns the page, so the
items table below swaps to the filtered rows. Clicking the active card
or "Show all" clears the filter and the table returns to the unfiltered
view. Cards with a count of zero are rendered disabled (faded, not
clickable) so the user can still see every measured category.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from .streamlit_run_kpi_specs import KPI_LABELS, FETCHER_NAMES, state_key


def get_active_filter(run_key: str) -> str | None:
    """Return the active KPI category key for ``run_key`` (or None)."""
    return st.session_state.get(state_key(run_key))


def render_kpi_filter_bar(run: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """Render the KPI toggle row; each click updates the session state."""
    run_key = run["run_key"]
    sk = state_key(run_key)
    active = st.session_state.get(sk)
    with st.container(horizontal=True):
        _render_show_all(sk, active, run_key, items)
        for spec in _kpi_specs(run):
            _render_toggle_button(sk, active, run_key, *spec)


def resolve_filtered_rows(run_key: str, active: str | None,
                          items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Return ``(rows, caption)`` to render in the items slot for ``active``."""
    if active is None or active not in KPI_LABELS:
        return items, "items"
    from ....core.database import order_runs_read_filters as _filters
    fetcher = getattr(_filters, FETCHER_NAMES[active])
    return fetcher(run_key), KPI_LABELS[active].lower()


def _render_show_all(sk: str, active: str | None, run_key: str,
                     items: list[dict[str, Any]]) -> None:
    """Render the leading 'Show all' button that clears the active filter."""
    if st.button(
        f"Show all · {len(items)}",
        icon=":material/format_list_bulleted:",
        disabled=len(items) == 0,
        type="secondary" if active is not None else "primary",
        key=f"kpi_show_all_{run_key}",
        width="stretch",
    ):
        _activate(sk, None)


def _render_toggle_button(sk: str, active: str | None, run_key: str,
                          key: str, label: str, count: int, icon: str) -> None:
    """Render one KPI toggle button and handle its click."""
    is_active = active == key
    if st.button(
        f"{label} · {count}",
        icon=icon,
        disabled=count <= 0,
        type="primary" if is_active else "secondary",
        key=f"kpi_{key}_{run_key}",
        width="stretch",
    ):
        _activate(sk, None if is_active else key)


def _activate(state_key: str, value: str | None) -> None:
    """Set the active filter and rerun so downstream widgets rerender."""
    if value is None:
        st.session_state.pop(state_key, None)
    else:
        st.session_state[state_key] = value
    st.rerun()


def _kpi_specs(run: dict[str, Any]) -> list[tuple[str, str, int, str]]:
    """Return (key, label, count, icon) tuples for the toggle row."""
    return [
        ("matched", "Matched", int(run.get("matched", 0) or 0),
         ":material/check_circle:"),
        ("flagged", "Flagged", int(run.get("flagged", 0) or 0),
         ":material/warning:"),
        ("not_orderable", "Not-orderable",
         int(run.get("not_orderable", 0) or 0), ":material/block:"),
        ("ordered", "Ordered qty", int(run.get("total_ordered", 0) or 0),
         ":material/shopping_cart:"),
    ]
