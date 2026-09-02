"""Add/remove dialog for Excel target catalogs.

The dialog lets the operator drop in a fresh vendor pricelist without
ever editing ``state/config.yaml``. The selected name becomes the
target key (a transliterated slug) and the file bytes are written
under ``artifacts/uploaded-excel-targets/<key>.xlsx``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from ..excel_targets_manager import (
    DEFAULT_TARGET_NAME,
    _normalise_name,
    add_excel_target,
    remove_excel_target,
    user_added_targets,
)


ADD_DIALOG_KEY = "excel_target_add_dialog_open"


@st.dialog("Add Excel target catalog", width="large")
def _add_excel_target_dialog(config_path: Path) -> None:
    """Render the Add Excel target dialog body."""
    name = st.text_input(
        "Catalog name",
        value=DEFAULT_TARGET_NAME,
        key="excel_target_add_name",
        help=(
            "Free-form label. The catalog key is derived from this name "
            "(letters/digits joined by underscores)."
        ),
    )
    uploaded = st.file_uploader(
        "Catalog file",
        type=["xlsx"],
        key="excel_target_add_file",
        help="Drop the .xlsx you want to match against.",
    )
    st.caption("Column names inside the catalog")
    cols = st.columns(3)
    name_col = cols[0].text_input(
        "Product name column",
        value="صنف",
        key="excel_target_add_name_col",
    )
    price_col = cols[1].text_input(
        "Price column",
        value="سعر",
        key="excel_target_add_price_col",
    )
    discount_col = cols[2].text_input(
        "Discount column",
        value="الخصم",
        key="excel_target_add_discount_col",
    )
    code_col = st.text_input(
        "Code column (optional)",
        value="",
        key="excel_target_add_code_col",
    )
    st.caption(
        "Default values match the columns of a typical vendor pricelist. "
        "Adjust them to whatever your file actually uses."
    )

    preview_key = _normalise_name(name or DEFAULT_TARGET_NAME)
    st.write(f"Key that will be added: `{preview_key}`")

    cancel, add = st.columns(2)
    if cancel.button("Cancel", use_container_width=True):
        st.session_state[ADD_DIALOG_KEY] = False
        st.rerun()
    add_disabled = uploaded is None
    if add.button(
        "Add Excel target",
        type="primary",
        use_container_width=True,
        disabled=add_disabled,
    ):
        result = add_excel_target(
            config_path=config_path,
            display_name=name or DEFAULT_TARGET_NAME,
            uploaded_file=uploaded,
            name_col=name_col or "صنف",
            price_col=price_col or "سعر",
            discount_col=discount_col or "الخصم",
            code_col=code_col or "",
        )
        st.success(
            f"Added `{result.target_key}` → {result.catalog_path}"
        )
        st.session_state[ADD_DIALOG_KEY] = False
        st.session_state["excel_target_added_toast"] = result.target_key
        st.rerun()


def maybe_open_add_dialog(config_path: Path) -> None:
    """Open the Add Excel target dialog if the operator pressed the button."""
    if st.session_state.get(ADD_DIALOG_KEY):
        _add_excel_target_dialog(config_path)


def render_add_excel_target_button(config_path: Path) -> None:
    """Render the `+ Add Excel target` button that opens the dialog."""
    if st.button(
        "+ Add Excel target",
        key="excel_target_add_button",
        help=(
            "Add a new Excel catalog to state/config.yaml without "
            "editing the file by hand."
        ),
    ):
        st.session_state[ADD_DIALOG_KEY] = True
        st.rerun()


def render_excel_target_removal_buttons(
    config_path: Path, excel_target_keys: list[str]
) -> None:
    """Backwards-compatible wrapper kept for older callers.

    The trash buttons are now rendered inline next to each Excel target
    checkbox in :func:`streamlit_profile_fields._render_target_checkboxes`.
    This stub stays so external imports do not break; it just renders an
    empty container.
    """
    return None


@st.dialog("Remove Excel target", width="medium")
def _confirm_remove_dialog(config_path: Path, target_key: str) -> None:
    """Show a Yes/No dialog and drop the target on confirmation."""
    st.warning(
        f"Remove user-added target `{target_key}`? "
        "This deletes the config entry; the catalog file is left in place."
    )
    confirm, cancel = st.columns(2)
    if confirm.button(
        "Yes, remove it",
        type="primary",
        key=f"excel_target_dialog_confirm_{target_key}",
    ):
        if remove_excel_target(config_path, target_key):
            st.session_state["excel_target_removed_toast"] = True
        st.session_state["excel_target_remove_pending"] = None
        st.rerun()
    if cancel.button(
        "Cancel",
        key=f"excel_target_dialog_cancel_{target_key}",
    ):
        st.session_state["excel_target_remove_pending"] = None
        st.rerun()


def maybe_open_remove_dialog(config_path: Path) -> None:
    """Open the remove confirmation dialog if the operator pressed 🗑."""
    pending = st.session_state.get("excel_target_remove_pending")
    if pending:
        _confirm_remove_dialog(config_path, pending)


__all__ = [
    "ADD_DIALOG_KEY",
    "DEFAULT_TARGET_NAME",
    "maybe_open_add_dialog",
    "render_add_excel_target_button",
    "render_excel_target_removal_buttons",
]
