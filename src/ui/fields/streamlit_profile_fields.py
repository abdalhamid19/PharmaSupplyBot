"""Profile and run configuration fields for Streamlit order form."""

import streamlit as st

OrderRunFields = tuple[str, str, int, bool, bool, bool, str, bool, float, int, int]


def profile_run_fields(app_config) -> OrderRunFields:
    """Return the order form fields related to profile execution."""
    fields, _ = profile_run_fields_with_workers(app_config)
    return fields


def profile_run_fields_with_workers(app_config) -> tuple[OrderRunFields, int]:
    """Return the order form fields and item workers count."""
    profile_mode = st.radio("Run target", ["Single profile", "All profiles"], horizontal=True)
    profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0)
    limit = st.number_input("Item limit", min_value=0, max_value=100000, value=1500)

    advanced_options = _render_advanced_options(app_config)
    
    fields = (
        str(profile_mode), str(profile_key), int(limit),
        *advanced_options[:-1]
    )
    return fields, advanced_options[-1]


def _render_advanced_options(app_config):
    """Render advanced options expander."""
    with st.expander("⚙️ Advanced Options", expanded=False):
        start_item = st.number_input("Start item number", min_value=1, value=1)
        end_item = st.number_input("End item number (0 for unlimited)", min_value=0, value=0)
        debug_browser = st.checkbox("Debug browser", value=False)
        resume = st.checkbox("Resume from previous summary", value=False)
        match_only = st.checkbox("Match only without adding to cart", value=False)
        execution_mode = st.selectbox("Execution mode", ["auto", "api", "browser"], index=0, help="auto uses API when a safe contract exists, then falls back to browser.")
        item_workers = item_workers_field(app_config)
        highest_discount = st.checkbox("Highest discount only", value=False)
        min_discount = st.number_input("Minimum discount percent", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    
    return (bool(debug_browser), bool(resume), bool(match_only), str(execution_mode), bool(highest_discount), float(min_discount), int(start_item), int(end_item), int(item_workers))


def item_workers_field(app_config) -> int:
    """Return the requested item-level worker count for one order run."""
    runtime = getattr(app_config, "runtime", None)
    configured = int(getattr(runtime, "item_workers", 1) or 1)
    return int(
        st.number_input(
            "Item workers",
            min_value=1,
            max_value=4,
            value=max(1, min(configured, 4)),
            help="Split this Excel file across isolated Chromium workers for one profile.",
        )
    )
