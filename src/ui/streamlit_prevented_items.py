"""Prevented-items tab rendering for the Streamlit GUI."""

from __future__ import annotations

from .streamlit_order_form import render_prevented_items_manager


def render_prevented_items_tab() -> None:
    """Render the dedicated prevented-items management page."""
    render_prevented_items_manager()
