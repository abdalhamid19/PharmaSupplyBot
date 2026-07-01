"""Overview tab rendering for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from ..streamlit_shared import (
    ARTIFACTS_DIR,
    ORDER_ITEMS_DIR,
    PREVENTED_ITEMS_DIR,
    REMOVE_ITEMS_DIR,
    load_csv_rows,
)


def render_overview(app_config, config_path: Path) -> None:
    """Render high-level project status and local environment details."""
    input_files = sorted(ORDER_ITEMS_DIR.glob("*.xlsx")) if ORDER_ITEMS_DIR.exists() else []
    prevented_files = sorted(PREVENTED_ITEMS_DIR.glob("*.xlsx")) if PREVENTED_ITEMS_DIR.exists() else []
    remove_files = sorted(REMOVE_ITEMS_DIR.glob("*.xlsx")) if REMOVE_ITEMS_DIR.exists() else []
    summary_path = ARTIFACTS_DIR / "wardany" / "order_item_summary.csv"
    summary_rows = load_csv_rows(summary_path)
    render_overview_metrics(app_config, input_files, prevented_files, summary_rows)
    render_settings_section(app_config, app_config.matching, config_path)
    render_profile_table(app_config.profiles)
    render_input_files_table(input_files, prevented_files, remove_files)
    render_latest_summary_rows(summary_rows)


def render_settings_section(app_config, matching_config, config_path: Path) -> None:
    """Render toggle switches for application settings."""
    with st.expander("⚙️ Automation & Matching Settings", expanded=False):
        from ...core.config.config_updater import update_matching_flags_in_config
        col1, col2 = st.columns(2)
        with col1:
            auto_save, re_review_auto = _render_col1_settings(matching_config)
        with col2:
            re_review_approved = _render_col2_settings(
                matching_config, config_path, auto_save, re_review_auto
            )


def _render_col1_settings(matching_config):
    """Render column 1 settings toggles."""
    st.write("🛡️ **Auto-Save Verified Matches**")
    st.caption("Automatically save perfectly matched items so you never have to review them again.")
    auto_save = st.toggle("Enable Auto-Save", value=matching_config.enable_auto_save_verified_match)
    st.write("⚠️ **Re-review Missing Auto-Matches**")
    st.caption("If an auto-saved item is completely out of stock, send it back to manual review to find an alternative.")
    re_review_auto = st.toggle("Re-review Auto-Matches", value=matching_config.enable_auto_match_re_review_on_fail)
    return auto_save, re_review_auto


def _render_col2_settings(matching_config, config_path, auto_save, re_review_auto):
    """Render column 2 settings toggles and save button."""
    from ...core.config.config_updater import update_matching_flags_in_config
    st.write("⚠️ **Re-review Missing Approved Matches**")
    st.caption("If a manually approved item is out of stock, send it back to manual review to find an alternative.")
    re_review_approved = st.toggle("Re-review Approved", value=matching_config.enable_approved_match_re_review_on_fail)
    st.write("💾 **Save Configuration**")
    st.caption(f"Save these settings directly to `{config_path.name}`.")
    if st.button("Apply Changes", type="primary"):
        new_flags = {
            "enable_auto_save_verified_match": auto_save,
            "enable_auto_match_re_review_on_fail": re_review_auto,
            "enable_approved_match_re_review_on_fail": re_review_approved
        }
        update_matching_flags_in_config(config_path, new_flags)
        st.success("Settings saved successfully! They will apply on the next run.")
        st.rerun()
    return re_review_approved


def render_overview_metrics(app_config, input_files, prevented_files, summary_rows) -> None:
    """Render top-line project metrics for the overview tab."""
    metrics = st.columns(4)
    metrics[0].metric("Profiles", len(app_config.profiles))
    metrics[1].metric("Order Excel Files", len(input_files))
    metrics[2].metric("Recent Summary Rows", len(summary_rows))
    submit_order = "On" if app_config.runtime.submit_order else "Off"
    metrics[3].metric("Submit Order", submit_order)


def render_profile_table(profiles) -> None:
    """Render the configured profiles table."""
    st.subheader("Profiles")
    rows = [
        {
            "profile": k,
            "display_name": p.display_name,
            "state_file": f"{k}.json",
            "state_exists": (Path("state") / f"{k}.json").exists(),
        }
        for k, p in profiles.items()
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_input_files_table(input_files, prevented_files, remove_files) -> None:
    """Render the available Excel files table."""
    st.subheader("Available Order Excel Files")
    rows = file_table_rows(input_files, "order_items")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No order Excel files found under `data/input/order_items/`.")
    st.subheader("Available Prevented Excel Files")
    prevented_rows = file_table_rows(prevented_files, "prevented_items")
    if prevented_rows:
        st.dataframe(pd.DataFrame(prevented_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No prevented-items Excel files found under `data/input/prevented_items/`.")
    st.subheader("Available Remove-Cart Excel Files")
    remove_rows = file_table_rows(remove_files, "remove_items")
    if remove_rows:
        st.dataframe(pd.DataFrame(remove_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No remove-cart Excel files found under `data/input/remove_items/`.")


def file_table_rows(files, category) -> list:
    """Return display rows for one local Excel-file category."""
    return [
        {
            "file": str(file),
            "category": category,
            "size_kb": round(file.stat().st_size / 1024, 1),
        }
        for file in files
    ]


def render_latest_summary_rows(summary_rows) -> None:
    """Render the latest summary rows block when data exists."""
    if summary_rows:
        st.subheader("Latest Order Summary Rows")
        st.dataframe(pd.DataFrame(summary_rows[-10:]), use_container_width=True, hide_index=True)
