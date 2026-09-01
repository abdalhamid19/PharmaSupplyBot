"""Profile, Excel-target, and run configuration fields for Streamlit order form."""

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
    """Return the order form fields and item workers count.

    The "Run target" selector combines Tawreed profiles and Excel targets
    into one multiselect so an operator can run matching against any
    combination of live Tawreed profiles and offline Excel catalogs in
    the same submission.
    """
    profile_keys = list(app_config.profiles.keys())
    excel_target_keys = list(app_config.enabled_excel_targets().keys())
    target_options = [
        _format_target_label(key, kind, app_config)
        for kind, keys in (("profile", profile_keys), ("excel-target", excel_target_keys))
        for key in keys
    ]
    target_value_by_label = {
        _format_target_label(key, kind, app_config): (kind, key)
        for kind, keys in (
            ("profile", profile_keys),
            ("excel-target", excel_target_keys),
        )
        for key in keys
    }

    selected_labels = st.multiselect(
        "Run target",
        options=target_options,
        default=target_options[: min(1, len(target_options))],
        help=(
            "Pick any mix of Tawreed profiles and Excel-target catalogs. "
            "Each one is matched independently against the order Excel."
        ),
    )
    selected_pairs = [target_value_by_label[label] for label in selected_labels]

    if any(kind == "profile" for kind, _ in selected_pairs):
        profile_mode = "Single profile" if len(selected_pairs) == 1 else "Multi"
    else:
        profile_mode = "Excel targets only"
    primary_profile = next(
        (key for kind, key in selected_pairs if kind == "profile"),
        profile_keys[0] if profile_keys else "",
    )

    profile_key = st.selectbox(
        "Primary profile (for resume/preview only)",
        options=profile_keys or [""],
        index=0,
        disabled=not profile_keys,
        help=(
            "Used to scope resume and the watched summary CSV. "
            "Excel-target runs do not need this — pick any profile."
        ),
    )
    limit = st.number_input("Item limit", min_value=0, max_value=100000, value=1500)

    excel_target_uploads = _render_excel_target_upload_widgets(
        selected_pairs, app_config
    )

    advanced_options = _render_advanced_options(app_config)
    fields = OrderRunFields(
        profile_mode=str(profile_mode),
        selected_targets=tuple(
            f"{kind}:{key}" for kind, key in selected_pairs
        ),
        profile_key=str(primary_profile or profile_key),
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
    return fields, int(advanced_options[-1]), excel_target_uploads


def _render_excel_target_upload_widgets(
    selected_pairs: list[tuple[str, str]],
    app_config: AppConfig,
) -> dict[str, dict[str, object]]:
    """Render one Excel target source selector per selected target.

    Each enabled Excel target in the selection exposes three modes:

    * ``Configured`` — use the catalog path the GUI resolves from
      ``data/input/excel target/<key>.xlsx`` (the existing default).
    * ``Existing file`` — pick another ``.xlsx`` already on disk under
      ``data/input/excel target/``.
    * ``Upload file`` — upload a brand-new catalog from the operator's
      machine. The uploaded bytes are written to
      ``artifacts/uploaded-excel-targets/<key>.xlsx`` so the subprocess
      can read them through ``--excel-target-path key=<path>``.

    The returned mapping is ``{target_key: {"mode": ..., "path": ..., "upload": ...}}``.
    """
    uploads: dict[str, dict[str, object]] = {}
    excel_target_keys = [
        key for kind, key in selected_pairs if kind == "excel-target"
    ]
    if not excel_target_keys:
        return uploads
    excel_options = available_excel_target_options()
    st.markdown("##### Excel target source")
    for target_key in excel_target_keys:
        target_cfg = app_config.excel_targets.get(target_key)
        label = getattr(target_cfg, "display_name", "") or target_key
        cols = st.columns([2, 3])
        with cols[0]:
            mode = st.radio(
                f"Source for {label} ({target_key})",
                ["Configured", "Existing file", "Upload file"],
                key=f"excel_target_source_{target_key}",
                horizontal=True,
                help=(
                    "Configured = the catalog that ships with config.yaml. "
                    "Existing file = another .xlsx under data/input/excel target/. "
                    "Upload file = drag-and-drop a fresh catalog."
                ),
            )
        path = ""
        upload = None
        if mode == "Existing file":
            with cols[1]:
                if excel_options:
                    path = str(
                        st.selectbox(
                            f"Catalog path for {target_key}",
                            excel_options,
                            key=f"excel_target_path_{target_key}",
                        )
                    )
                else:
                    path = str(
                        st.text_input(
                            f"Catalog path for {target_key}",
                            key=f"excel_target_path_text_{target_key}",
                        )
                    )
        elif mode == "Upload file":
            with cols[1]:
                upload = st.file_uploader(
                    f"Upload catalog for {target_key}",
                    type=["xlsx"],
                    key=f"excel_target_upload_{target_key}",
                )
        uploads[target_key] = {"mode": mode, "path": path, "upload": upload}
    return uploads


def _format_target_label(key: str, kind: str, app_config: AppConfig) -> str:
    """Return one human-friendly label for a profile or excel-target."""
    if kind == "profile":
        profile = app_config.profiles.get(key)
        display = profile.display_name if profile else key
        return f"👤 Tawreed profile — {display} ({key})"
    return f"📊 Excel target — {key}"


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


__all__ = [
    "OrderRunFields",
    "profile_run_fields",
    "profile_run_fields_with_workers",
    "item_workers_field",
]