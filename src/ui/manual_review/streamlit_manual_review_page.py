"""Dedicated Manual Review tab for evaluating top candidate matches."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterable
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
    st.markdown("Select an artifact run to evaluate matches and correct them.")
    if render_running_remove_cart_controls("manual_review") or render_running_search_controls():
        return
    run_groups = _group_runs_by_id(_available_runs_with_candidates())
    if not run_groups:
        st.info("No matching runs with manual review candidates found.")
        render_saved_decisions()
        return
    run_ids = [run_id for run_id, _ in run_groups]
    directories_by_id = dict(run_groups)
    selected_run_id = st.selectbox(
        "Select Run", run_ids,
        index=0,
        format_func=lambda run_id: _format_run_group(
            run_id, directories_by_id[run_id]
        ),
    )
    if selected_run_id:
        _render_selected_run(directories_by_id[selected_run_id], app_config)
        render_saved_decisions()


def _render_selected_run(selected_run, app_config=None):
    """Render all source directories belonging to one logical run."""
    run_dirs = _coerce_run_dirs(selected_run)
    run_context = _primary_run_dir(run_dirs)
    paths = sorted(
        path
        for run_dir in run_dirs
        for path in run_dir.glob("manual_review_*.csv")
    )
    if paths:
        rows = []
        seen_rows = set()
        for path in paths:
            for row in load_csv_rows(path):
                key = (
                    str(row.get("item_code", "")),
                    str(row.get("item_name", "")),
                    str(row.get("matching_source", row.get("source_kind", ""))),
                    str(row.get("matching_source_label", row.get("source_label", ""))),
                    str(row.get("target_key", row.get("excel_target_key", ""))),
                )
                if key in seen_rows:
                    continue
                seen_rows.add(key)
                rows.append(row)
        if rows:
            render_manual_review_editor(rows, run_context)
            st.divider()
    render_run_candidates(run_dirs, app_config)


def _group_runs_by_id(runs: Iterable[Path]) -> list[tuple[str, tuple[Path, ...]]]:
    """Collapse source-specific artifact directories into logical runs."""
    grouped: dict[str, list[Path]] = {}
    for run_dir in runs:
        grouped.setdefault(run_dir.name, []).append(run_dir)
    return [
        (run_id, tuple(sorted(grouped[run_id], key=str)))
        for run_id in sorted(
            grouped,
            key=lambda run_id: max(_run_recency_key(path) for path in grouped[run_id]),
            reverse=True,
        )
    ]


def _format_run_group(run_id: str, run_dirs: tuple[Path, ...]) -> str:
    """Return a concise selectbox label listing every source in the run."""
    sources = ", ".join(
        f"{run_dir.parent.parent.name}/{run_dir.parent.name}"
        for run_dir in run_dirs
    )
    return f"{run_id} — {sources}"


def _coerce_run_dirs(value) -> tuple[Path, ...]:
    """Accept the old single-Path API and the new grouped-run API."""
    if isinstance(value, Path):
        return (value,)
    return tuple(value)


def _primary_run_dir(run_dirs: tuple[Path, ...]) -> Path:
    """Choose the Tawreed directory for shared run actions when available."""
    for run_dir in run_dirs:
        if run_dir.parent.parent.name == "order":
            return run_dir
    return run_dirs[0]


def _available_runs_with_candidates() -> list[Path]:
    """Return artifact runs that can provide a review or candidate view.

    Generic Tawreed runs use ``order_item_summary`` while Excel-target runs
    use ``match_only_summary`` and may emit one candidate JSONL per target.
    Discovery therefore checks all review artifact markers.
    """
    runs: set[Path] = set()
    if not ARTIFACTS_DIR.exists():
        return []
    for category_dir in _safe_child_directories(ARTIFACTS_DIR):
        for source_dir in _safe_child_directories(category_dir):
            for run_dir in _safe_child_directories(source_dir):
                if _has_review_artifacts(run_dir):
                    runs.add(run_dir)
    # The selectbox uses index 0 when the user has not made a choice yet, so
    # order by the run id first instead of the full path. Sorting by the full
    # path made the artifact category/source name decide the default and could
    # surface an older run.
    return sorted(runs, key=_run_recency_key, reverse=True)


def _safe_child_directories(path) -> tuple[Path, ...]:
    """List readable child directories without breaking the whole UI.

    Test/runtime artifact folders can temporarily be locked by Windows or
    owned by another process. Such a folder is unrelated to Manual Review and
    must not prevent accessible order runs from being displayed.
    """
    try:
        children = tuple(path.iterdir())
    except OSError:
        return ()
    readable: list[Path] = []
    for child in children:
        try:
            if child.is_dir():
                readable.append(child)
        except OSError:
            continue
    return tuple(readable)


def _run_recency_key(path: Path) -> tuple[str, int, int, str]:
    """Return a deterministic newest-first key for an artifact run.

    Normal run directory names are timestamp-like (``YYYYMMDD_HHMM``), making
    lexical ordering chronological. When one command creates Tawreed and
    Excel-target directories with the same id, the directory containing more
    review items wins the default selection. Modification time breaks ties.
    """
    run_id = path.name
    timestamp_key = run_id if _is_timestamp_run_id(run_id) else ""
    try:
        modified_ns = path.stat().st_mtime_ns
    except OSError:
        modified_ns = 0
    return timestamp_key, _review_item_count(path), modified_ns, str(path)


def _review_item_count(run_dir: Path) -> int:
    """Count persisted review-item records without parsing candidate payloads."""
    count = 0
    for candidate_file in run_dir.glob("manual_review_candidates_*.jsonl"):
        try:
            with candidate_file.open("r", encoding="utf-8") as handle:
                count += sum(1 for line in handle if line.strip())
        except OSError:
            continue
    return count


def _is_timestamp_run_id(value: str) -> bool:
    """Return whether ``value`` starts with the standard run timestamp."""
    date, separator, time_part = value.partition("_")
    return bool(
        separator
        and len(date) == 8
        and date.isdigit()
        and len(time_part) >= 4
        and time_part[:4].isdigit()
    )


def _has_review_artifacts(run_dir: Path) -> bool:
    """Return whether a directory contains a review-relevant artifact."""
    markers = (
        "order_item_summary_*.csv",
        "match_only_summary_*.csv",
        "manual_review_*.csv",
        "manual_review_candidates_*.jsonl",
    )
    try:
        return any(any(run_dir.glob(pattern)) for pattern in markers)
    except OSError:
        return False


# ============ Candidate Rendering ============

def render_run_candidates(run_dir: Path | Iterable[Path], app_config=None) -> None:
    """Render merged evaluation cards for every source in one run."""
    run_dirs = _coerce_run_dirs(run_dir)
    run_context = _primary_run_dir(run_dirs)
    st.subheader(f"Candidates from run: {run_context.name}")
    st.caption(f"Combined sources: {len(run_dirs)}")
    candidates_dict = _load_group_candidates(run_dirs)
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
        visible_options = _limit_candidates_by_source(options, display_limit)
        _render_item_card(item_key, item, visible_options, run_context, store)


def _load_group_candidates(
    run_dirs: Iterable[Path],
) -> dict[str, list[ReviewCandidateOption]]:
    """Merge source-specific candidate artifacts without losing provenance."""
    merged: dict[str, list[ReviewCandidateOption]] = {}
    seen: dict[str, set[tuple[str, ...]]] = {}
    for run_dir in run_dirs:
        for item_key, options in load_review_candidates(run_dir).items():
            bucket = merged.setdefault(item_key, [])
            bucket_seen = seen.setdefault(item_key, set())
            for raw_option in options:
                option = _candidate_with_run_source(raw_option, run_dir)
                identity = (
                    option.store_product_id,
                    option.name_en,
                    option.name_ar,
                    option.matching_source,
                    option.matching_source_label,
                    option.target_key,
                    option.source_file,
                    option.excel_target_row_key,
                )
                if identity in bucket_seen:
                    continue
                bucket_seen.add(identity)
                bucket.append(option)
    return merged


def _candidate_with_run_source(
    option: ReviewCandidateOption, run_dir: Path
) -> ReviewCandidateOption:
    """Backfill provenance for legacy candidates from their artifact path."""
    if option.matching_source:
        return option
    category = run_dir.parent.parent.name
    source_name = run_dir.parent.name
    if category == "order":
        return replace(
            option,
            matching_source="tawreed",
            matching_source_label=source_name,
        )
    if category == "excel-target":
        return replace(
            option,
            matching_source="excel-target",
            matching_source_label=source_name,
            target_key=option.target_key or source_name,
            excel_target_key=option.excel_target_key or source_name,
        )
    return replace(
        option,
        matching_source=category or "legacy-unknown",
        matching_source_label=source_name,
    )


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


def _limit_candidates_by_source(
    options: list[ReviewCandidateOption], limit: int
) -> list[ReviewCandidateOption]:
    """Keep at least one candidate visible for every source when possible."""
    if limit <= 0 or not options:
        return []
    groups = _group_options_by_source(options)
    if len(groups) == 1:
        return options[:limit]

    selected: list[ReviewCandidateOption] = []
    selected_ids: set[int] = set()
    for _, group in groups[:limit]:
        selected.append(group[0])
        selected_ids.add(id(group[0]))
    if len(selected) >= limit:
        return selected[:limit]
    for option in options:
        if id(option) in selected_ids:
            continue
        selected.append(option)
        if len(selected) >= limit:
            break
    return selected


def _configured_candidate_limit(app_config=None) -> int:
    """Return configured Manual Review candidate count with default fallback."""
    matching = getattr(app_config, "matching", None)
    value = getattr(matching, "manual_review_display_candidate_limit", 5)
    return max(1, int(value))


def _filter_and_prepare_items(candidates_dict, store, hide_completed):
    """Filter completed candidate scopes while preserving other sources."""
    all_items = list(candidates_dict.items())
    if not hide_completed:
        return all_items
    filtered_items = []
    for item_key, options in all_items:
        parts = item_key.split("::", 1)
        item_code = parts[0].upper()
        item_name = parts[1].upper() if len(parts) > 1 else "Unknown"
        saved_decisions = store.lookup_all(item_code, item_name)
        if not saved_decisions:
            filtered_items.append((item_key, options))
            continue
        remaining_options = [
            option
            for option in options
            if not any(
                _decision_covers_candidate_scope(saved, option)
                for saved in saved_decisions
            )
        ]
        if remaining_options:
            filtered_items.append((item_key, remaining_options))
    return filtered_items


def _decision_covers_candidate_scope(decision, option: ReviewCandidateOption) -> bool:
    """Return whether a saved decision belongs to this candidate source scope."""
    option_source = _normalized_source(option.matching_source)
    if not option_source:
        # Legacy candidate artifacts did not record a source and retain their
        # historical item-level completion behaviour.
        return True
    decision_source = _normalized_source(getattr(decision, "matching_source", ""))
    if decision_source != option_source:
        return False
    if option_source != "excel-target":
        return True
    option_target = option.excel_target_key or option.target_key
    decision_target = getattr(decision, "excel_target_key", "")
    return bool(option_target and decision_target and option_target == decision_target)


def _normalized_source(value: object) -> str:
    """Normalize source aliases used by old and new artifacts."""
    return str(value or "").strip().lower().replace("_", "-")


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
        _render_candidate_provenance(options)
        render_selection_form(item, options, run_dir, store, item_key)


def _render_candidate_provenance(options: list[ReviewCandidateOption]) -> None:
    """Display every distinct source represented in the merged review card."""
    scopes: dict[tuple[str, ...], ReviewCandidateOption] = {}
    for option in options:
        scope = (
            option.matching_source,
            option.matching_source_label,
            option.target_key,
            option.source_file,
            option.identity_evidence_kind,
        )
        scopes.setdefault(scope, option)
    for option in scopes.values():
        details = [f"Matching source: {option.matching_source or 'legacy/unknown'}"]
        if option.matching_source_label:
            details.append(f"Source label: {option.matching_source_label}")
        if option.target_key:
            details.append(f"Target: {option.target_key}")
        if option.source_file:
            details.append(f"File: {option.source_file}")
        if option.identity_evidence_kind:
            details.append(f"Identity evidence: {option.identity_evidence_kind}")
        if option.identity_evidence_kind == "review_fuzzy":
            details.append("Review-only fuzzy candidate; human approval required")
        if option.candidate_method:
            details.append(f"Candidate method: {option.candidate_method}")
        if option.review_status:
            details.append(f"Review status: {option.review_status}")
        if option.score_margin:
            details.append(f"Score margin: {option.score_margin:.2f}")
        if option.shared_brand_tokens:
            details.append(
                "Shared brand tokens: " + ", ".join(option.shared_brand_tokens)
            )
        if option.excel_target_source_row:
            details.append(f"Target row: {option.excel_target_source_row}")
        if option.excel_target_row_key:
            details.append(f"Target row key: {option.excel_target_row_key}")
        st.caption(" · ".join(details))


# ============ Form Rendering ============

def _candidate_scope_key(option: ReviewCandidateOption) -> tuple[str, str]:
    """Return the persisted supplier scope represented by one candidate."""
    source = _normalized_source(
        getattr(option, "matching_source", "")
        or getattr(option, "source_kind", "")
    ) or "legacy-unknown"
    if source == "excel-target":
        scope = (
            getattr(option, "excel_target_key", "")
            or getattr(option, "target_key", "")
            or getattr(option, "matching_source_label", "")
            or getattr(option, "source_file", "")
            or source
        )
    else:
        scope = (
            getattr(option, "matching_source_label", "")
            or getattr(option, "source_file", "")
            or getattr(option, "supplier", "")
            or source
        )
    return source, str(scope)


def _group_options_by_source(
    options: list[ReviewCandidateOption],
) -> list[tuple[tuple[str, str], list[ReviewCandidateOption]]]:
    """Group candidates so each supplier/Excel target gets one selector."""
    grouped: dict[tuple[str, str], list[ReviewCandidateOption]] = {}
    for option in options:
        grouped.setdefault(_candidate_scope_key(option), []).append(option)
    return list(grouped.items())


def _scope_display_name(scope: tuple[str, str]) -> str:
    """Return a concise source label for a grouped selector."""
    source, value = scope
    return value if value else source


def render_selection_form(
    item: Item,
    options: list[ReviewCandidateOption],
    run_dir: Path,
    store: ManualReviewStore,
    item_key: str
) -> None:
    """Render the selection UI and handle mutual exclusivity of inputs."""
    groups = _group_options_by_source(options)
    if len(groups) > 1:
        _render_multi_source_selection_form(item, groups, run_dir, store, item_key)
        return
    idx_key = f"radio_{item_key}"
    nm_key = f"nm_{item_key}"
    query_key = f"query_{item_key}"
    callbacks = _create_callbacks(item, options, run_dir, store, idx_key, nm_key, query_key)
    _render_form_ui(options, idx_key, nm_key, query_key, callbacks)


def _render_multi_source_selection_form(
    item: Item,
    groups: list[tuple[tuple[str, str], list[ReviewCandidateOption]]],
    run_dir: Path,
    store: ManualReviewStore,
    item_key: str,
) -> None:
    """Render one independent candidate selector for every source scope."""
    nm_key = f"nm_{item_key}"
    query_key = f"query_{item_key}"
    radio_keys: list[str] = []
    for position, (scope, group_options) in enumerate(groups):
        radio_key = f"radio_{item_key}_{position}"
        radio_keys.append(radio_key)
        st.markdown(f"**Select best match — {_scope_display_name(scope)}:**")
        radio_opts = _build_radio_opts(group_options)

        def _save_group_selection(
            *,
            group_options=group_options,
            radio_key=radio_key,
        ) -> None:
            st.session_state[nm_key] = False
            st.session_state[query_key] = ""
            _save(
                item,
                group_options,
                int(st.session_state.get(radio_key, 0)),
                False,
                "",
                run_dir,
                store,
            )

        st.radio(
            "Select best match:",
            range(len(radio_opts)),
            format_func=lambda index, radio_opts=radio_opts: radio_opts[index],
            key=radio_key,
            on_change=_save_group_selection,
        )

    _render_multi_source_fallback_controls(
        item,
        radio_keys,
        nm_key,
        query_key,
        run_dir,
        store,
    )


def _render_multi_source_fallback_controls(
    item: Item,
    radio_keys: list[str],
    nm_key: str,
    query_key: str,
    run_dir: Path,
    store: ManualReviewStore,
) -> None:
    """Render the legacy item-level no-match/query fallback controls."""
    def _clear_group_radios() -> None:
        for radio_key in radio_keys:
            st.session_state[radio_key] = 0

    def on_no_match() -> None:
        if st.session_state.get(nm_key, False):
            _clear_group_radios()
            st.session_state[query_key] = ""
            _save(item, [], 0, True, "", run_dir, store)

    def on_query() -> None:
        query = str(st.session_state.get(query_key, "") or "")
        if query.strip():
            _clear_group_radios()
            st.session_state[nm_key] = False
            _save(item, [], 0, False, query, run_dir, store)

    col1, col2 = st.columns(2)
    with col1:
        st.checkbox("No match exists (all sources)", key=nm_key, on_change=on_no_match)
    with col2:
        st.text_input("Or query (all sources):", key=query_key, on_change=on_query)


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
        if opt.identity_evidence_kind == "review_fuzzy":
            label += " | Review-only"
        source = getattr(opt, "matching_source", "") or getattr(opt, "source_kind", "")
        if source:
            label += f" | Source: {source}"
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
    "_group_options_by_source",
    "_configured_candidate_limit",
]
