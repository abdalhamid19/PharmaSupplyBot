"""Order form helpers for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from .prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    PREVENTED_CODE_COLUMN,
    PREVENTED_NAME_COLUMN,
    PreventedItem,
    add_prevented_item,
    load_prevented_items,
    remove_prevented_item,
    save_prevented_items,
)
from .streamlit_uploads import available_excel_options


def order_form_values(app_config) -> tuple[bool, dict[str, object]]:
    """Return the submitted order form values."""
    prevented_items_path = render_prevented_items_manager()
    with st.form("order_form"):
        values = order_form_fields(app_config, prevented_items_path)
        submitted = st.form_submit_button("Run Order")
    return bool(submitted), values


def order_form_fields(app_config, prevented_items_path: Path | None = None) -> dict[str, object]:
    """Return the order form field values."""
    input_mode, excel_path_str, upload = excel_source_fields()
    profile_mode, profile_key, limit, debug_browser, resume, highest_discount, min_discount = (
        profile_run_fields(app_config)
    )
    return {
        "input_mode": input_mode,
        "excel_path_str": excel_path_str,
        "upload": upload,
        "profile_mode": profile_mode,
        "profile_key": profile_key,
        "limit": int(limit),
        "debug_browser": bool(debug_browser),
        "resume": bool(resume),
        "highest_discount": bool(highest_discount),
        "min_discount_percent": float(min_discount),
        "prevented_items_excel": str(prevented_items_path or DEFAULT_PREVENTED_ITEMS_PATH),
    }


def render_prevented_items_manager(
    path: Path = DEFAULT_PREVENTED_ITEMS_PATH,
) -> Path:
    """Render controls for the persistent prevented-items list."""
    st.markdown("**Prevented items**")
    existing_prevented_path = st.selectbox(
        "Existing prevented-items file",
        prevented_excel_options(path),
        index=0,
    )
    if st.button("Use selected prevented-items file") and existing_prevented_path:
        persist_existing_prevented_items_file(Path(existing_prevented_path), path)
        st.success(f"Saved prevented-items list to `{path}`.")
    uploaded_file = st.file_uploader(
        "Upload prevented-items XLSX",
        type=["xlsx"],
        key="prevented_items_upload",
    )
    if uploaded_file is not None:
        persist_uploaded_prevented_items(uploaded_file, path)
        st.success(f"Saved prevented-items list to `{path}`.")
    try:
        prevented_items = load_prevented_items(path)
    except Exception as error:
        st.error(f"Could not load prevented-items list: {error}")
        prevented_items = []
    render_prevented_items_editor(prevented_items, path)
    return path


def persist_uploaded_prevented_items(uploaded_file, path: Path = DEFAULT_PREVENTED_ITEMS_PATH) -> Path:
    """Persist an uploaded prevented-items XLSX as the active saved list."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(uploaded_file.getvalue())
    return path


def persist_existing_prevented_items_file(
    source_path: Path,
    path: Path = DEFAULT_PREVENTED_ITEMS_PATH,
) -> Path:
    """Persist an existing XLSX file as the active prevented-items list."""
    if source_path.resolve() == path.resolve():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source_path.read_bytes())
    return path


def render_prevented_items_editor(
    prevented_items: list[PreventedItem],
    path: Path = DEFAULT_PREVENTED_ITEMS_PATH,
) -> None:
    """Render add/remove controls for the prevented-items list."""
    add_col, remove_col = st.columns(2)
    with add_col:
        new_code = st.text_input("Prevented item code", key="prevented_item_code")
        new_name = st.text_input("Prevented item name", key="prevented_item_name")
        if st.button("Add prevented item"):
            updated_items = add_prevented_item(prevented_items, new_code, new_name)
            save_prevented_items(updated_items, path)
            st.rerun()
    with remove_col:
        remove_options = prevented_item_options(prevented_items)
        selected_key = st.selectbox(
            "Remove prevented item",
            remove_options or [""],
            index=0,
        )
        if st.button("Remove selected prevented item") and selected_key:
            code, name = selected_key.split("\t", 1)
            updated_items = remove_prevented_item(prevented_items, code, name)
            save_prevented_items(updated_items, path)
            st.rerun()
    if prevented_items:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        PREVENTED_CODE_COLUMN: item.code,
                        PREVENTED_NAME_COLUMN: item.name,
                    }
                    for item in prevented_items
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No prevented items saved.")


def prevented_item_options(prevented_items: list[PreventedItem]) -> list[str]:
    """Return selectbox options that preserve prevented item identity."""
    return [f"{item.code}\t{item.name}" for item in prevented_items]


def prevented_excel_options(path: Path = DEFAULT_PREVENTED_ITEMS_PATH) -> list[str]:
    """Return available XLSX choices for the prevented-items list."""
    options = [str(option) for option in available_excel_options()]
    default_option = str(path)
    if default_option not in options:
        options.insert(0, default_option)
    else:
        options.remove(default_option)
        options.insert(0, default_option)
    return options


def excel_source_fields() -> tuple[str, str, object]:
    """Return the order form fields related to Excel input selection."""
    input_mode = st.radio(
        "Excel source",
        ["Existing file", "Upload file"],
        horizontal=True,
    )
    excel_path_str = existing_excel_path(input_mode, available_excel_options())
    return input_mode, excel_path_str, uploaded_excel_file(input_mode)


def profile_run_fields(app_config) -> tuple[str, str, int, bool, bool, bool, float]:
    """Return the order form fields related to profile execution."""
    profile_mode = st.radio("Run target", ["Single profile", "All profiles"], horizontal=True)
    profile_key = st.selectbox("Profile", list(app_config.profiles.keys()), index=0)
    limit = st.number_input("Item limit", min_value=0, max_value=100000, value=50)
    resume = st.checkbox("Resume from previous summary", value=True)
    highest_discount = st.checkbox("Highest discount only", value=False)
    min_discount = st.number_input(
        "Minimum discount percent",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
    )
    debug_browser = st.checkbox("Debug browser", value=False)
    return (
        str(profile_mode),
        str(profile_key),
        int(limit),
        bool(debug_browser),
        bool(resume),
        bool(highest_discount),
        float(min_discount),
    )


def existing_excel_path(input_mode: str, excel_options: list[str]) -> str:
    """Return the selected existing Excel path when that input mode is active."""
    if input_mode != "Existing file":
        return ""
    if excel_options:
        return str(st.selectbox("Excel file", excel_options, index=0))
    return str(st.text_input("Excel file path", ""))


def uploaded_excel_file(input_mode: str):
    """Return the uploaded Excel file when upload mode is active."""
    return st.file_uploader("Upload Excel", type=["xlsx"]) if input_mode == "Upload file" else None
