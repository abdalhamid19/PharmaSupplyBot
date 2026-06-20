"""Streamlit helpers for Manual Review database availability."""

from __future__ import annotations

import streamlit as st

from ..core.manual_review_store import ManualReviewStore


def manual_review_store_or_stop() -> ManualReviewStore:
    """Return the CockroachDB manual-review store or stop the Streamlit page."""
    try:
        return ManualReviewStore()
    except Exception as error:
        st.error(f"Manual review database is not available: {error}")
        st.info("Set DB_PASSWORD and DB_SSLMODE=require in .env, then restart Streamlit.")
        st.stop()
