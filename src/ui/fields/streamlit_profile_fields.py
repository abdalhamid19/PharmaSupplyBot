"""Profile, Excel-target, and run configuration fields for Streamlit order form.

The Run Order form exposes two complementary UI surfaces:

* A simple **checkbox group** ("What to run against?") lets the operator
  pick any combination of Tawreed profiles and Excel-target catalogs. Each
  checkbox is rendered directly in the page so the operator never has to
  open a dropdown to discover what is available — that was the failure
  mode of the previous multiselect, which the operator reported as
  "the upload widget never appears" even after the config had an Excel
  target configured.
* A dedicated **Excel target source panel** below the main form
  renders one radio + (optional) file picker per selected Excel target
  catalog. The panel lives outside ``st.form`` so changing the radio
  does not trigger a form rerun.
"""

from __future__ import annotations

from typing import NamedTuple

import streamlit as st

from src.core.config.config_models import AppConfig
from ..streamlit_uploads import available_excel_target_options


class OrderRunFields(NamedTuple):
    """Order form fields covering both Tawreed profiles and Excel targets."""

    profile_mode: str
    selected_targets: tuple[str, ...]
    profile_key: str
    limit: int
    debug_browser: bool
    resume: bool
    match_only: bool
    execution_mode: str
    highest_discount: bool
    min_discount_percent: float
    start_item: int
    end_item: int


def profile_run_fields(app_config) -> OrderRunFields:
    """Return the order form fields related to profile execution."""
    fields, _ = profile_run_fields_with_workers(app_config)
    return fields


def profile_run_fields_with_workers(app_config) -> tuple[OrderRunFields, int]:
    """Render the Run target picker + advanced options and snapshot their state.

    Every widget is rendered outside ``st.form`` and its value is mirrored
    to ``st.session_state`` so the rest of the page (including the
    Excel target source panel) can read the latest selection without a
    submit cycle.
    """
    profile_keys = list(app_config.profiles.keys())
    excel_target_keys = list(app_config.enabled_excel_targets().keys())

    selected_pairs = _render_target_checkboxes(app_config, profile_keys, excel_target_keys)
    primary_profile = next(
        (key for kind, key in selected_pairs if kind == "profile"),
        profile_keys[0] if profile_keys else "",
    )

    profile_key = st.selectbox(
        "Primary profile (for resume/preview only)",
        options=profile_keys or [""],
        index=_safe_index(profile_keys, primary_profile),
        disabled=not profile_keys,
        help=(
            "Used to scope resume and the watched summary CSV. "
            "Excel-target runs do not need this — pick any profile."
        ),
        key="order_form_primary_profile",
    )
    limit = st.number_input(
        "Item limit",
        min_value=0,
        max_value=100000,
        value=1500,
        key="order_form_item_limit",
    )

    advanced_options = _render_advanced_options(app_config)
    if any(kind == "profile" for kind, _ in selected_pairs):
        profile_mode = "Single profile" if len(selected_pairs) == 1 else "Multi"
    else:
        profile_mode = "Excel targets only"

    st.session_state["excel_target_selected_targets"] = tuple(
        f"{kind}:{key}" for kind, key in selected_pairs
    )
    st.session_state["order_form_advanced"] = {
        "limit": int(advanced_options[0]) if False else int(limit),
        "debug_browser": bool(advanced_options[0]),
        "resume": bool(advanced_options[1]),
        "match_only": bool(advanced_options[2]),
        "execution_mode": str(advanced_options[3]),
        "highest_discount": bool(advanced_options[4]),
        "min_discount_percent": float(advanced_options[5]),
        "start_item": int(advanced_options[6]),
        "end_item": int(advanced_options[7]),
    }
    st.session_state["order_form_item_workers"] = int(advanced_options[8])

    fields = OrderRunFields(
        profile_mode=str(profile_mode),
        selected_targets=tuple(f"{kind}:{key}" for kind, key in selected_pairs),
        profile_key=str(profile_key or primary_profile),
        limit=int(limit),
        debug_browser=bool(advanced_options[0]),
        resume=bool(advanced_options[1]),
        match_only=bool(advanced_options[2]),
        execution_mode=str(advanced_options[3]),
        highest_discount=bool(advanced_options[4]),
        min_discount_percent=float(advanced_options[5]),
        start_item=int(advanced_options[6]),
        end_item=int(advanced_options[7]),
    )
    return fields, int(advanced_options[-1])


def _safe_index(options: list[str], value: str) -> int:
    """Return the index of ``value`` in ``options`` or 0 if missing."""
    try:
        return options.index(value)
    except ValueError:
        return 0


def _render_target_checkboxes(
    app_config: AppConfig, profile_keys: list[str], excel_target_keys: list[str]
) -> list[tuple[str, str]]:
    """Render one ``st.checkbox`` per configured target so every option is visible."""
    selected_pairs: list[tuple[str, str]] = []
    st.markdown("##### What to run against?")
    cols = st.columns(2) if profile_keys or excel_target_keys else [st]
    col_idx = 0
    for key in profile_keys:
        with cols[col_idx % len(cols)]:
            profile = app_config.profiles.get(key)
            display = profile.display_name if profile else key
            if st.checkbox(
                f"👤 Tawreed profile — {display} ({key})",
                value=True,
                key=f"run_target_profile_{key}",
            ):
                selected_pairs.append(("profile", key))
        col_idx += 1
    for key in excel_target_keys:
        with cols[col_idx % len(cols)]:
            if st.checkbox(
                f"📊 Excel target ({key})",
                value=False,
                key=f"run_target_excel_{key}",
                help=(
                    "Tick to also match against this Excel target catalog. "
                    "The upload widget appears below after ticking."
                ),
            ):
                selected_pairs.append(("excel-target", key))
        col_idx += 1
    if not selected_pairs:
        st.warning("Tick at least one target above to enable the Run Order button.")
    st.session_state["excel_target_selected_targets"] = tuple(
        f"{kind}:{key}" for kind, key in selected_pairs
    )
    return selected_pairs


def render_excel_target_sources(app_config) -> dict[str, dict[str, object]]:
    """Render the Excel-target source controls (outside the form)."""
    selected_targets = st.session_state.get("excel_target_selected_targets") or ()
    uploads: dict[str, dict[str, object]] = {}
    excel_target_keys = [
        token.split(":", 1)[1]
        for token in selected_targets
        if isinstance(token, str) and token.startswith("excel-target:")
    ]
    if not excel_target_keys:
        return uploads
    excel_options = available_excel_target_options()
    st.markdown("##### 📊 Excel target source")
    st.caption(
        "Pick one or more existing files under data/input/excel target/ or "
        "upload a fresh catalog. Upload file persists the bytes under "
        "`artifacts/uploaded-excel-targets/<key>.xlsx`."
    )
    for target_key in excel_target_keys:
        st.markdown(f"**{target_key}**")
        mode = st.radio(
            "Source",
            ["Existing file", "Upload file"],
            key=f"excel_target_source_{target_key}",
            horizontal=True,
            label_visibility="collapsed",
            help=(
                "Existing file = pick one or more .xlsx files under "
                "data/input/excel target/. "
                "Upload file = drag-and-drop a fresh catalog."
            ),
        )
        paths: list[str] = []
        upload = None
        if mode == "Existing file":
            if excel_options:
                select_all_key = f"excel_target_select_all_{target_key}"
                select_all = st.checkbox(
                    "Select all",
                    value=False,
                    key=select_all_key,
                    help="Tick to include every .xlsx in data/input/excel target/.",
                )
                default_selection: list[str] = list(excel_options) if select_all else []
                selection_key = f"excel_target_path_{target_key}"
                chosen = st.multiselect(
                    "Catalog files",
                    excel_options,
                    default=default_selection,
                    key=selection_key,
                    label_visibility="collapsed",
                    help="Pick one or more catalogs. Tick 'Select all' to include every .xlsx.",
                )
                paths = [str(p) for p in chosen]
            else:
                paths = [
                    str(
                        st.text_input(
                            "Catalog path",
                            key=f"excel_target_path_text_{target_key}",
                            label_visibility="collapsed",
                        )
                    )
                ]
        elif mode == "Upload file":
            upload = st.file_uploader(
                f"Upload catalog for {target_key}",
                type=["xlsx"],
                key=f"excel_target_upload_{target_key}",
                help="Drag-and-drop or browse to upload this Excel target catalog.",
            )
        st.divider()
        uploads[target_key] = {"mode": mode, "paths": paths, "upload": upload}
    return uploads


def _render_advanced_options(app_config):
    """Render advanced options expander."""
    with st.expander("⚙️ Advanced Options", expanded=False):
        start_item = st.number_input(
            "Start item number", min_value=1, value=1, key="order_form_start_item"
        )
        end_item = st.number_input(
            "End item number (0 for unlimited)",
            min_value=0,
            value=0,
            key="order_form_end_item",
        )
        debug_browser = st.checkbox("Debug browser", value=False, key="order_form_debug_browser")
        resume = st.checkbox(
            "Resume from previous summary", value=False, key="order_form_resume"
        )
        match_only = st.checkbox(
            "Match only without adding to cart", value=False, key="order_form_match_only"
        )
        execution_mode = st.selectbox(
            "Execution mode",
            ["auto", "api", "browser"],
            index=0,
            key="order_form_execution_mode",
            help="auto uses API when a safe contract exists, then falls back to browser.",
        )
        item_workers = item_workers_field(app_config)
        highest_discount = st.checkbox(
            "Highest discount only", value=False, key="order_form_highest_discount"
        )
        min_discount = st.number_input(
            "Minimum discount percent",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0,
            key="order_form_min_discount",
        )

    return (
        bool(debug_browser),
        bool(resume),
        bool(match_only),
        str(execution_mode),
        bool(highest_discount),
        float(min_discount),
        int(start_item),
        int(end_item),
        int(item_workers),
    )


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
            key="order_form_item_workers_widget",
            help="Split this Excel file across isolated Chromium workers for one profile.",
        )
    )


__all__ = [
    "OrderRunFields",
    "profile_run_fields",
    "profile_run_fields_with_workers",
    "render_excel_target_sources",
    "item_workers_field",
]