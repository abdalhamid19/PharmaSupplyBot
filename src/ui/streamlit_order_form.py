"""Order form helpers for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ..core.prevented_items import DEFAULT_PREVENTED_ITEMS_PATH
from .streamlit_ai_fields import ai_matching_fields, matching_risk_fields
from .streamlit_excel_fields import excel_source_fields, order_excel_options
from .streamlit_prevented_items import (
    render_prevented_items_manager,
    add_and_save_prevented_item,
)
from .streamlit_profile_fields import profile_run_fields_with_workers, OrderRunFields


def order_form_values(app_config) -> tuple[bool, dict[str, object]]:
    """Return the submitted order form values."""
    with st.form("order_form"):
        values = order_form_fields(app_config, DEFAULT_PREVENTED_ITEMS_PATH)
        submitted = st.form_submit_button("Run Order")
    return bool(submitted), values


def order_form_fields(
    app_config, prevented_items_path: Path | None = None
) -> dict[str, object]:
    """Return the order form field values."""
    input_mode, excel_path_str, upload = excel_source_fields()
    run_fields, item_workers = profile_run_fields_with_workers(app_config)
    values = _order_form_values(
        input_mode,
        excel_path_str,
        upload,
        run_fields,
        item_workers,
        prevented_items_path,
    )
    values.update(ai_matching_fields())
    return values


def _order_form_values(
    input_mode: str,
    excel_path_str: str,
    upload: object,
    run_fields: OrderRunFields,
    item_workers: int,
    prevented_items_path: Path | None,
) -> dict[str, object]:
    """Build serializable order form values from collected widget fields."""
    values = {
        "input_mode": input_mode,
        "excel_path_str": excel_path_str,
        "upload": upload,
        "item_workers": int(item_workers),
        "prevented_items_excel": str(
            prevented_items_path or DEFAULT_PREVENTED_ITEMS_PATH
        ),
    }
    values.update(_order_run_values(run_fields))
    return values


def _order_run_values(run_fields: OrderRunFields) -> dict[str, object]:
    """Build values related to the selected order run target/options."""
    profile_mode, profile_key, limit, debug_browser, resume, match_only = run_fields[:6]
    extended_vals = _extended_order_run_values(run_fields)
    execution_mode, high_disc, min_disc, start_item, end_item = extended_vals
    return {
        "profile_mode": profile_mode,
        "profile_key": profile_key,
        "limit": int(limit),
        "debug_browser": bool(debug_browser),
        "resume": bool(resume),
        "match_only": bool(match_only),
        "execution_mode": str(execution_mode),
        "highest_discount": bool(high_disc),
        "min_discount_percent": float(min_disc),
        "start_item": int(start_item),
        "end_item": int(end_item),
    }


def _extended_order_run_values(run_fields: OrderRunFields) -> tuple[str, bool, float, int, int]:
    """Return execution mode and discount controls with old-test tuple compatibility."""
    tail = run_fields[6:]
    if len(tail) == 2:
        high_disc, min_disc = tail
        return "auto", bool(high_disc), float(min_disc), 1, 0
    if len(tail) == 3:
        execution_mode, high_disc, min_disc = tail
        return str(execution_mode), bool(high_disc), float(min_disc), 1, 0
    execution_mode, high_disc, min_disc, start_item, end_item = tail
    return str(execution_mode), bool(high_disc), float(min_disc), int(start_item), int(end_item)
