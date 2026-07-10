"""Dedicated Manual Review tab for evaluating top candidate matches."""

from __future__ import annotations

from pathlib import Path
import streamlit as st

from ...core.manual_review.manual_review_candidate_store import load_review_candidates
from ...core.manual_review.manual_review_candidates import ReviewCandidateOption
from ...core.manual_review.manual_review_selection import decision_from_selection
from ...core.manual_review.manual_review_store import ManualReviewStore
from ...core.utils.excel import Item
from .streamlit_manual_review import (
    render_manual_review_editor,
    manual_review_store_or_stop,
    render_running_search_controls,
)
from .streamlit_manual_review_page_saved import render_saved_decisions
from ..streamlit_remove_cart import render_running_remove_cart_controls
from ..streamlit_shared import ARTIFACTS_DIR, load_csv_rows


def render_manual_review_tab(app_config=None) -> None:
    """Render the full manual review workflow with candidate options."""
    st.title("Manual Review")
    st.markdown("Select an artifact run to evaluate AI matches and correct them.")
    if render_running_remove_cart_controls("manual_review") or render_running_search_controls():
        return
    runs = _available_runs_with_candidates()
    if not runs:
        st.info("No matching runs with manual review candidates found.")
        render_saved_decisions()
        return
    selected_run = st.selectbox(
        "Select Run", runs,
        format_func=lambda r: f"{r.parent.parent.name} / {r.parent.name} / {r.name}"
    )
    if selected_run:
        _render_selected_run(selected_run, app_config)
        render_saved_decisions()


def _render_selected_run(selected_run, app_config=None):
    """Render the selected run's manual review."""
    paths = list(selected_run.glob("manual_review_*.csv"))
    if paths:
        rows = load_csv_rows(paths[0])
        if rows:
            render_manual_review_editor(rows, selected_run)
            st.divider()
    render_run_candidates(selected_run, app_config)


def _available_runs_with_candidates() -> list[Path]:
    runs = []
    if not ARTIFACTS_DIR.exists():
        return runs
    for c_dir in filter(lambda p: p.is_dir(), ARTIFACTS_DIR.iterdir()):
        for p_dir in filter(lambda p: p.is_dir(), c_dir.iterdir()):
            for r_dir in filter(lambda p: p.is_dir(), p_dir.iterdir()):
                if list(r_dir.glob("order_item_summary_*.csv")):
                    runs.append(r_dir)
    return sorted(runs, reverse=True)


# ============ Candidate Rendering ============

def render_run_candidates(run_dir: Path, app_config=None) -> None:
    """Render the evaluation cards for the selected run."""
    st.subheader(f"Candidates from run: {run_dir.name}")
    candidates_dict = load_review_candidates(run_dir)
    if not candidates_dict:
        st.success(
            "🎉 All items in this run were processed automatically! "
            "No manual review is required."
        )
        return
    store = manual_review_store_or_stop()
    hide_completed = st.checkbox("Hide completed items", value=True)
    display_limit = _candidate_display_limit(app_config)
    display_items = _filter_and_prepare_items(candidates_dict, store, hide_completed)
    page_items = _paginate_candidates(display_items)
    for item_key, options in page_items:
        item = _parse_item_from_key(item_key)
        _render_item_card(item_key, item, options[:display_limit], run_dir, store)


def _candidate_display_limit(app_config=None) -> int:
    """Return Manual Review candidate display count from config plus UI extra."""
    base_limit = _configured_candidate_limit(app_config)
    st.caption(f"Showing {base_limit} candidates per item from config by default.")
    extra = st.number_input(
        "Additional candidates to show per item",
        min_value=0,
        max_value=100,
        value=0,
        step=1,
        help="Adds this many saved candidates below the default visible options.",
    )
    return base_limit + int(extra)


def _configured_candidate_limit(app_config=None) -> int:
    """Return configured Manual Review candidate count with default fallback."""
    matching = getattr(app_config, "matching", None)
    value = getattr(matching, "manual_review_candidate_limit", 5)
    return max(1, int(value))


def _filter_and_prepare_items(candidates_dict, store, hide_completed):
    """Filter and prepare display items based on completion status."""
    all_items = list(candidates_dict.items())
    if not hide_completed:
        return all_items
    filtered_items = []
    for item_key, options in all_items:
        parts = item_key.split("::", 1)
        item_code = parts[0].upper()
        item_name = parts[1].upper() if len(parts) > 1 else "Unknown"
        if not store.lookup(item_code, item_name):
            filtered_items.append((item_key, options))
    return filtered_items


def _paginate_candidates(display_items):
    """Apply pagination to candidates list."""
    current_page = st.session_state.get("manual_review_page", 1)
    items_per_page = 50
    total_candidates = len(display_items)
    st.caption(f"📊 Candidates: {total_candidates} items")
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_candidates)
    if total_candidates > items_per_page:
        st.caption(f"Showing candidates {start_idx + 1}-{end_idx} (matching page {current_page})")
    return display_items[start_idx:end_idx]


def _parse_item_from_key(item_key):
    """Parse Item object from item_key string."""
    parts = item_key.split("::", 1)
    item_code = parts[0].upper()
    item_name = parts[1].upper() if len(parts) > 1 else "Unknown"
    return Item(code=item_code, name=item_name, qty="1")


def _render_item_card(
    item_key: str,
    item: Item,
    options: list[ReviewCandidateOption],
    run_dir: Path,
    store: ManualReviewStore
) -> None:
    with st.expander(f"Review: {item.name} ({item.code})", expanded=True):
        st.markdown(f"**Requested Item:** {item.name}")
        render_selection_form(item, options, run_dir, store, item_key)


# ============ Form Rendering ============

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
    callbacks = _create_callbacks(item, options, run_dir, store, idx_key, nm_key, query_key)
    _render_form_ui(options, idx_key, nm_key, query_key, callbacks)


def _create_callbacks(item, options, run_dir, store, idx_key, nm_key, query_key):
    """Create callback functions for form interactions."""
    def _trigger_save():
        _save_from_state(item, options, run_dir, store, idx_key, nm_key, query_key)
    def on_radio():
        if st.session_state.get(idx_key, 0) > 0:
            st.session_state[nm_key], st.session_state[query_key] = False, ""
        _trigger_save()
    def on_nm():
        if st.session_state.get(nm_key, False):
            st.session_state[idx_key], st.session_state[query_key] = 0, ""
        _trigger_save()
    def on_query():
        if st.session_state.get(query_key, "").strip():
            st.session_state[idx_key], st.session_state[nm_key] = 0, False
        _trigger_save()
    return on_radio, on_nm, on_query


def _save_from_state(item, options, run_dir, store, idx_key, nm_key, query_key):
    """Persist the current widget state for one manual-review item."""
    _save(
        item, options, st.session_state.get(idx_key, 0),
        st.session_state.get(nm_key, False),
        st.session_state.get(query_key, ""), run_dir, store,
    )


def _render_form_ui(options, idx_key, nm_key, query_key, callbacks):
    """Render the form UI components."""
    on_radio, on_nm, on_query = callbacks
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


__all__ = [
    "render_manual_review_tab",
    "render_run_candidates",
    "render_selection_form",
    "_configured_candidate_limit",
]
