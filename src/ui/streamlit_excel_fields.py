"""Excel input fields for Streamlit order form."""

from pathlib import Path

import streamlit as st

from .streamlit_uploads import available_excel_options


def excel_source_fields() -> tuple[str, str, object]:
    """Return the order form fields related to Excel input selection."""
    input_mode = st.radio(
        "Excel source",
        ["Existing file", "Upload file"],
        horizontal=True,
    )
    excel_path_str = existing_excel_path(input_mode, order_excel_options())
    return input_mode, excel_path_str, uploaded_excel_file(input_mode)


def order_excel_options(prevented_items_path: Path = None) -> list[str]:
    """Return existing Excel files that can be used as order source sheets."""
    from ..core.prevented_items import DEFAULT_PREVENTED_ITEMS_PATH

    prevented_path = str(prevented_items_path or DEFAULT_PREVENTED_ITEMS_PATH)
    return [
        option
        for option in available_excel_options()
        if str(Path(option)) != prevented_path
    ]


def existing_excel_path(input_mode: str, excel_options: list[str]) -> str:
    """Return the selected existing Excel path when that input mode is active."""
    if input_mode != "Existing file":
        return ""
    if excel_options:
        return str(st.selectbox("Excel file", excel_options, index=0))
    return str(st.text_input("Excel file path", ""))


def uploaded_excel_file(input_mode: str):
    """Return the uploaded Excel file when upload mode is active."""
    return (
        st.file_uploader("Upload Excel", type=["xlsx"])
        if input_mode == "Upload file"
        else None
    )
