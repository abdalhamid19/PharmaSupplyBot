"""Prevented items management UI for Streamlit order form."""

from pathlib import Path

import pandas as pd
import streamlit as st

from ..core.prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    PREVENTED_CODE_COLUMN,
    PREVENTED_ITEMS_DIR,
    PREVENTED_NAME_COLUMN,
    PreventedItem,
    add_prevented_item,
    load_prevented_items,
    remove_prevented_item,
    save_prevented_items,
)
from .streamlit_uploads import available_excel_options


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


def persist_uploaded_prevented_items(
    uploaded_file, path: Path = DEFAULT_PREVENTED_ITEMS_PATH
) -> Path:
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
            add_and_save_prevented_item(prevented_items, new_code, new_name, path)
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


def add_and_save_prevented_item(
    prevented_items: list[PreventedItem],
    code: object,
    name: object,
    path: Path = DEFAULT_PREVENTED_ITEMS_PATH,
) -> list[PreventedItem]:
    """Add one prevented item and persist the updated list."""
    updated_items = add_prevented_item(prevented_items, code, name)
    save_prevented_items(updated_items, path)
    return updated_items


def prevented_excel_options(path: Path = DEFAULT_PREVENTED_ITEMS_PATH) -> list[str]:
    """Return available XLSX choices for the prevented-items list."""
    options = []
    if PREVENTED_ITEMS_DIR.exists():
        options = [str(option) for option in sorted(PREVENTED_ITEMS_DIR.glob("*.xlsx"))]
    default_option = str(path)
    if default_option not in options:
        options.insert(0, default_option)
    else:
        options.remove(default_option)
        options.insert(0, default_option)
    return options
