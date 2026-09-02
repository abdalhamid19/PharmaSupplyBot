"""Excel input fields for Streamlit order form.

The order Excel source widgets (existing file / upload file radio + the
file uploader itself) live **outside** ``st.form`` in the parent page.
That is the only way the file uploader reacts immediately when the
operator flips the radio to "Upload file" — a file uploader that is
declared inside ``st.form`` is deferred until the form is submitted, so
the operator has to click "Run Order" once for the uploader to even
appear. We mirror the selected mode into ``st.session_state`` so the
matching file picker renders synchronously and the downstream code can
read the chosen file on the same rerun.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ..streamlit_uploads import available_excel_options, resolve_excel_path


SOURCE_KEY = "order_excel_source_mode"
SOURCE_EXISTING = "Existing file"
SOURCE_UPLOAD = "Upload file"


def render_excel_source_fields() -> None:
    """Render the order Excel source widgets and mirror their state.

    Side effects: writes ``st.session_state["order_excel_path"]`` (string)
    and ``st.session_state["order_excel_upload"]`` (UploadedFile or None).
    The form code that builds the CLI command reads these two values.
    """
    excel_options = order_excel_options()
    if SOURCE_KEY not in st.session_state:
        st.session_state[SOURCE_KEY] = SOURCE_EXISTING

    mode = st.radio(
        "Excel source",
        [SOURCE_EXISTING, SOURCE_UPLOAD],
        horizontal=True,
        key=SOURCE_KEY,
        help=(
            "Existing file = pick from data/input/order_items/. "
            "Upload file = drag-and-drop a fresh order Excel."
        ),
    )
    if mode == SOURCE_EXISTING:
        if excel_options:
            default_path = excel_options[0]
            current = st.session_state.get("order_excel_path") or default_path
            if current not in excel_options:
                current = default_path
            st.session_state["order_excel_path"] = str(
                st.selectbox(
                    "Excel file",
                    excel_options,
                    index=excel_options.index(current),
                )
            )
        else:
            st.session_state["order_excel_path"] = str(
                st.text_input("Excel file path", "")
            )
        st.session_state["order_excel_upload"] = None
    else:
        st.session_state["order_excel_upload"] = st.file_uploader(
            "Upload Excel",
            type=["xlsx"],
            help="Drag-and-drop or browse to upload the order Excel file.",
        )
        st.session_state["order_excel_path"] = ""


def order_excel_options(prevented_items_path: Path = None) -> list[str]:
    """Return existing Excel files that can be used as order source sheets."""
    from ...core.ordering.prevented_items import DEFAULT_PREVENTED_ITEMS_PATH

    prevented_path = str(prevented_items_path or DEFAULT_PREVENTED_ITEMS_PATH)
    return [
        option
        for option in available_excel_options()
        if str(Path(option)) != prevented_path
    ]


def resolve_order_excel_path() -> Path | None:
    """Return a usable Excel path from the session state."""
    upload = st.session_state.get("order_excel_upload")
    path_str = st.session_state.get("order_excel_path") or ""
    return resolve_excel_path(path_str, upload)


__all__ = [
    "render_excel_source_fields",
    "order_excel_options",
    "resolve_order_excel_path",
    "SOURCE_EXISTING",
    "SOURCE_UPLOAD",
]