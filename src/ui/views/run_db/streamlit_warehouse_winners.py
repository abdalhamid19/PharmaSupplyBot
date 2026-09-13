"""Warehouse-first view of the persisted lowest purchase prices."""

import streamlit as st

from ....core.database.order_runs_read import (
    fetch_run_warehouse_exclusions,
    fetch_run_warehouse_winners,
)
from .warehouse_winner_export import (
    build_warehouse_zip, safe_filename, warehouse_frame, warehouse_groups,
)


@st.cache_data(max_entries=8, show_spinner=False)
def _download(rows: list[dict]) -> bytes:
    """Cache by persisted content so a new offer invalidates the export."""
    return build_warehouse_zip(rows)


def render_warehouse_winners(run_key: str) -> None:
    """Show all winners before the existing, independently filtered details."""
    st.caption(
        "Price comparison only: this section is not the actual Tawreed basket. "
        "Use the actual basket section above for successful additions."
    )
    st.subheader("الأصناف الفائزة بأقل سعر شراء حسب المخزن")
    st.caption(
        "مقارنة العروض المتاحة المحفوظة في هذا التشغيل؛ كل صنف يظهر لدى مخزن واحد. "
        "العملة المعتمدة لجميع العروض هي الجنيه المصري."
    )
    st.caption("كمية Excel قد تكون علامة توافر بقيمة 1 وليست رصيد مخزون فعليًا.")
    rows = fetch_run_warehouse_winners(run_key)
    _render_exclusions(run_key)
    if not rows:
        st.info("لا توجد أصناف فائزة بعروض متاحة محفوظة لهذا التشغيل.")
        return
    _render_download(run_key, rows)
    _render_groups(rows)


def _render_exclusions(run_key: str) -> None:
    excluded = fetch_run_warehouse_exclusions(run_key)
    if excluded:
        st.caption(
            f"عدد الأصناف التي لا يوجد لها عرض متاح يحقق شروط السعر والخصم "
            f"المحفوظة: {len(excluded)}"
        )

def _render_download(run_key: str, rows: list[dict]) -> None:
    st.download_button(
        "تحميل جميع المخازن", data=_download(rows),
        file_name=f"{safe_filename(run_key)}.zip", mime="application/zip",
        key=f"warehouse_download:{run_key}", on_click="ignore",
    )


def _render_groups(rows: list[dict]) -> None:
    for (source, _), group in warehouse_groups(rows):
        with st.container(border=True):
            st.subheader(group[0]["store_name"])
            label = "Excel target" if source == "excel-target" else "توريد"
            st.caption(f"{label} · {len(group)} صنف")
            st.dataframe(warehouse_frame(group), width="stretch", hide_index=True)
