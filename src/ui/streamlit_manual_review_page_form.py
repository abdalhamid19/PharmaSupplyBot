"""Form rendering and state management for manual review selections."""

from __future__ import annotations

from pathlib import Path
import streamlit as st

from ..core.manual_review_candidates import ReviewCandidateOption
from ..core.manual_review_selection import decision_from_selection
from ..core.manual_review_store import ManualReviewStore
from ..core.utils.excel import Item


def render_selection_form(
    item: Item,
    options: list[ReviewCandidateOption],
    run_dir: Path,
    store: ManualReviewStore,
    item_key: str
) -> None:
    """Render the selection UI and handle mutual exclusivity of inputs."""
    idx_key = f"radio_{item_key}"
    nm_key = f"nm_{item_key}"
    query_key = f"query_{item_key}"

    def _trigger_save() -> None:
        idx = st.session_state.get(idx_key, 0)
        not_matching = st.session_state.get(nm_key, False)
        query = st.session_state.get(query_key, "")
        _save(item, options, idx, not_matching, query, run_dir, store)

    def on_radio() -> None:
        if st.session_state.get(idx_key, 0) > 0:
            st.session_state[nm_key] = False
            st.session_state[query_key] = ""
        _trigger_save()

    def on_nm() -> None:
        if st.session_state.get(nm_key, False):
            st.session_state[idx_key] = 0
            st.session_state[query_key] = ""
        _trigger_save()

    def on_query() -> None:
        if st.session_state.get(query_key, "").strip():
            st.session_state[idx_key] = 0
            st.session_state[nm_key] = False
        _trigger_save()

    radio_opts = _build_radio_opts(options)
    st.radio(
        "Select best match:", range(len(radio_opts)),
        format_func=lambda x: radio_opts[x],
        key=idx_key, on_change=on_radio
    )
    
    col1, col2 = st.columns(2)
    with col1:
        st.checkbox("No match exists", key=nm_key, on_change=on_nm)
    with col2:
        st.text_input("Or query:", key=query_key, on_change=on_query)


def _build_radio_opts(options: list[ReviewCandidateOption]) -> list[str]:
    radio_opts = ["None (Leave Unmatched)"]
    for i, opt in enumerate(options):
        avail = "✅" if opt.orderable else "⚠️ Unorderable"
        name = opt.name_en or opt.name_ar
        label = (
            f"[{i+1}] {name} | {opt.supplier} | "
            f"Qty: {opt.available_quantity} | سعر الجمهور: {opt.price} EGP | {avail}"
        )
        radio_opts.append(label)
    return radio_opts


def _save(
    item: Item, options: list, idx: int,
    not_matching: bool, query: str, run_dir: Path, store: ManualReviewStore
) -> None:
    opt = options[idx - 1] if idx > 0 else None
    decision = decision_from_selection(item, opt, not_matching, query, run_dir.name)
    
    if decision is None:
        return
    
    store.upsert(decision)
    _update_session_cache(item, decision, run_dir)
    st.toast(f"✅ Saved decision for {item.name}")


def _update_session_cache(item: Item, decision, run_dir: Path) -> None:
    """Update session cache to sync stats after saving decision."""
    cache_key = f"manual_review_cache_{run_dir.name}"
    if cache_key not in st.session_state:
        return
    
    for i, row in enumerate(st.session_state[cache_key]):
        if _is_matching_row(row, item):
            _apply_decision_to_row(st.session_state[cache_key][i], decision)
            break


def _is_matching_row(row: dict, item: Item) -> bool:
    """Check if row matches the item."""
    row_code = str(row.get("item_code", "")).strip()
    row_name = str(row.get("item_name", "")).strip().upper()
    item_code = str(item.code).strip()
    item_name = str(item.name).strip().upper()
    return row_code == item_code and row_name == item_name


def _apply_decision_to_row(row: dict, decision) -> None:
    """Apply decision fields to cache row."""
    row["approved_match"] = decision.approved
    row["not_matching"] = decision.manual_decision == "not_matching"
    if decision.correct_store_product_id:
        row["correct_store_product_id"] = decision.correct_store_product_id
    if decision.correct_product_name:
        row["correct_product_name"] = decision.correct_product_name
