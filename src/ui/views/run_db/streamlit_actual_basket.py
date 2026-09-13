"""Final Tawreed-basket and Excel Target purchasing views."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ....core.database.order_runs_read import (
    fetch_run_actual_basket,
    fetch_run_deferred_excel,
    fetch_run_match_only_simulation,
)
from .actual_basket_export import build_actual_basket_zip, safe_filename
from .match_only_purchase_simulation import (
    MatchOnlyPurchaseSimulation,
    build_match_only_purchase_simulation,
)


@st.cache_data(max_entries=8, show_spinner=False)
def _download_zip(
    tawreed_rows: list[dict], deferred_rows: list[dict]
) -> bytes:
    """Cache the ZIP by the persisted result rows it contains."""
    return build_actual_basket_zip(tawreed_rows, deferred_rows)


def render_actual_basket(run_key: str, *, run_mode: str = "") -> None:
    """Render the final purchasing result, grouped by its real destination."""
    deferred_rows = fetch_run_deferred_excel(run_key)
    tawreed_rows = fetch_run_actual_basket(run_key)
    simulation = None
    if run_mode == "match-only" and not tawreed_rows:
        simulation = build_match_only_purchase_simulation(
            fetch_run_match_only_simulation(run_key)
        )
        if simulation is not None:
            _render_simulated_excel_target_groups(simulation.excel_target_rows)

    st.subheader("نتيجة الشراء الفعلية")
    if tawreed_rows or deferred_rows:
        st.download_button(
            "تحميل ملفات Excel مستقلة لكل فرع (ZIP)",
            data=_download_zip(tawreed_rows, deferred_rows),
            file_name=f"{safe_filename(run_key)}.zip",
            mime="application/zip",
            key=f"actual_basket_download:{run_key}",
            on_click="ignore",
        )
        st.caption("يحتوي الملف المضغوط على ملف Excel مستقل لكل مخزن أو مصدر.")
    _render_excel_target_groups(deferred_rows)

    rows = tawreed_rows
    if rows:
        frame = pd.DataFrame(rows)
        st.caption(
            "هذه هي الأصناف التي أُضيفت بنجاح إلى سلة توريد، وليست مقارنة أسعار "
            "أو أصناف فائزة نظريًا."
        )

        st.subheader("أصناف سلة توريد الفعلية حسب المخزن")
        for store_name, group in frame.groupby("store_name", sort=True, dropna=False):
            display_name = store_name or "مخزن غير معروف"
            with st.container(border=True):
                st.subheader(display_name)
                st.caption(f"{group['item_key'].nunique()} صنف")
                st.dataframe(
                    group[
                        [
                            "item_code", "item_name", "matched_name", "requested_qty",
                            "ordered_qty", "public_price", "purchase_price",
                            "discount_percent", "status",
                        ]
                    ],
                    width="stretch",
                    hide_index=True,
                )
    else:
        st.info("لا توجد كميات أضيفت فعليًا إلى سلة توريد في هذا التشغيل.")
        if run_mode == "match-only":
            _render_match_only_simulation(simulation)


def _render_match_only_simulation(
    simulation: MatchOnlyPurchaseSimulation | None,
) -> None:
    """Show hypothetical destinations without presenting them as cart facts."""
    if simulation is None:
        st.info("لا توجد بيانات محفوظة كافية لمحاكاة هذا التشغيل.")
        return

    st.subheader("محاكاة السلة المحتملة حسب المخزن")
    st.caption(
        "محاكاة وليست إضافة فعلية: تستخدم العروض والأرصدة المسجلة وقت التشغيل "
        "وبوابة Excel Target وتفضيلات المخازن الافتراضية الحالية لأن قائمة التفضيل "
        "لا تُحفظ مع التشغيل. "
        "قد تتغير الأسعار والأرصدة عند الطلب الحقيقي."
    )
    _render_simulated_tawreed_groups(simulation.tawreed_rows)
    _render_simulation_notes(simulation)


def _render_simulated_tawreed_groups(rows: list[dict]) -> None:
    if not rows:
        return
    frame = pd.DataFrame(rows)
    for store_name, group in frame.groupby("store_name", sort=True, dropna=False):
        _render_simulated_tawreed_group(store_name, group)


def _render_simulated_tawreed_group(store_name: str, group: pd.DataFrame) -> None:
    with st.container(border=True):
        st.subheader(store_name or "مخزن غير معروف")
        st.caption(f"{group['item_key'].nunique()} صنف في المحاكاة")
        st.dataframe(
            group[
                [
                    "item_code", "item_name", "matched_name", "requested_qty",
                    "simulated_qty", "unfilled_qty", "available_qty",
                    "public_price", "purchase_price", "discount_percent",
                ]
            ],
            width="stretch",
            hide_index=True,
        )


def _render_simulation_notes(
    simulation: MatchOnlyPurchaseSimulation,
) -> None:
    if not simulation.tawreed_rows and not simulation.excel_target_rows:
        st.info(
            "لا توجد أصناف مؤهلة لمحاكاة سلة توريد؛ قد تكون بلا رصيد أو سعر صالح، "
            "أو تحتاج إلى مراجعة المطابقة."
        )
    if simulation.manual_review_items:
        st.caption(
            f"استُبعد {simulation.manual_review_items} صنفًا من المحاكاة "
            "لأن مطابقته تتطلب مراجعة يدوية."
        )
    if simulation.unsupported_strategy_items:
        st.caption(
            f"تعذرت محاكاة {simulation.unsupported_strategy_items} صنفًا "
            "لأن استراتيجية مخازنه غير مدعومة في المحاكاة."
        )


def _render_simulated_excel_target_groups(rows: list[dict]) -> None:
    """Show items the saved Excel price gate would keep out of Tawreed."""
    if not rows:
        return
    frame = pd.DataFrame(rows)
    source_names = frame["excel_target_source"].map(_excel_target_display_name)
    st.subheader("أصناف كانت ستُوجّه إلى Excel Target خارج سلة توريد")
    st.caption("الكمية التقديرية لكل صنف في Excel Target هي 1، وفق إعداد الطلب.")
    for target_name, group in frame.groupby(source_names, sort=True):
        _render_simulated_excel_target_group(target_name, group)


def _render_simulated_excel_target_group(
    target_name: str, group: pd.DataFrame
) -> None:
    with st.container(border=True):
        st.subheader(target_name)
        st.caption(f"{group['item_key'].nunique()} صنف")
        st.dataframe(
            group[
                [
                    "item_code", "item_name", "matched_name", "requested_qty",
                    "simulated_qty", "purchase_price", "discount_percent",
                ]
            ],
            width="stretch",
            hide_index=True,
        )


def _render_excel_target_groups(deferred: list[dict]) -> None:
    """Show deferred items first, grouped by the Excel source that won."""
    if not deferred:
        return
    deferred_frame = pd.DataFrame(deferred)
    st.subheader("أصناف Excel Target حسب المصدر")
    st.caption(
        "تظهر هذه الأصناف قبل مخازن توريد لأنها لم تُضف إلى السلة: "
        "سعر Excel Target أقل أو الفرق أقل من جنيه واحد."
    )
    target_labels = deferred_frame["excel_target_source"].map(
        _excel_target_display_name
    )
    for target_name, group in deferred_frame.groupby(target_labels, sort=True):
        with st.container(border=True):
            st.subheader(target_name)
            st.caption(f"{group['item_key'].nunique()} صنف")
            st.dataframe(
                group[
                        [
                            "item_code", "item_name", "matched_name", "requested_qty",
                            "excel_public_price", "excel_purchase_price",
                            "excel_discount_percent", "status",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )


def _excel_target_display_name(source: object) -> str:
    """Keep the configured target name while hiding its source-file suffix."""
    return str(source or "Excel Target").split("@", maxsplit=1)[0].strip()


__all__ = ["render_actual_basket"]
