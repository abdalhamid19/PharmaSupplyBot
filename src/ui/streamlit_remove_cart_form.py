"""Form rendering for remove-cart tab."""

from __future__ import annotations

import streamlit as st

from ..core.cart_removal_items import DEFAULT_REMOVE_ITEMS_PATH
from .streamlit_shared import REMOVE_ITEMS_DIR


def remove_cart_form_values(app_config) -> tuple[bool, dict[str, object]]:
    """Return submitted remove-cart form values."""
    with st.form("remove_cart_form"):
        input_mode = st.radio(
            "Removal Excel source",
            ["Existing file", "Upload file", "Saved not matching manual review"],
            horizontal=True,
        )
        excel_path_str = existing_remove_excel_path(input_mode, remove_excel_options())
        upload = (
            st.file_uploader("Upload removal Excel", type=["xlsx"])
            if input_mode == "Upload file"
            else None
        )
        profile_mode = st.radio(
            "Run target", ["Single profile", "All profiles"], horizontal=True
        )
        profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0)
        execution_mode = st.selectbox(
            "Execution mode",
            ["auto", "api", "browser"],
            index=0,
            help="auto uses API when a safe contract exists, then falls back to browser.",
        )
        debug_browser = st.checkbox("Debug browser", value=False)
        item_workers = remove_cart_item_workers_field(app_config)
        submitted = st.form_submit_button("Remove Cart Items")
    return bool(submitted), {
        "input_mode": input_mode,
        "excel_path_str": excel_path_str,
        "upload": upload,
        "profile_mode": str(profile_mode),
        "profile_key": str(profile_key),
        "execution_mode": str(execution_mode),
        "debug_browser": bool(debug_browser),
        "item_workers": int(item_workers),
    }


def existing_remove_excel_path(input_mode: str, excel_options: list[str]) -> str:
    """Return selected removal Excel path when existing-file mode is active."""
    if input_mode != "Existing file":
        return ""
    if excel_options:
        return str(st.selectbox("Removal Excel file", excel_options, index=0))
    return str(st.text_input("Removal Excel file path", str(DEFAULT_REMOVE_ITEMS_PATH)))


def remove_excel_options() -> list[str]:
    """Return existing cart-removal Excel files."""
    if not REMOVE_ITEMS_DIR.exists():
        return []
    return [str(path) for path in sorted(REMOVE_ITEMS_DIR.glob("*.xlsx"))]


def remove_cart_item_workers_field(app_config) -> int:
    """Return the requested item-level worker count for one cart-removal run."""
    runtime = getattr(app_config, "runtime", None)
    configured = int(getattr(runtime, "item_workers", 1) or 1)
    return int(
        st.number_input(
            "Item workers",
            min_value=1,
            max_value=4,
            value=max(1, min(configured, 4)),
            help="Split this remove Excel across isolated Chromium workers.",
        )
    )
