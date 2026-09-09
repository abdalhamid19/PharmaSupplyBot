"""Saved decisions rendering for the Manual Review tab."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from pathlib import Path
import pandas as pd
import streamlit as st

from ...core.manual_review.manual_review_store import ManualReviewStore
from .streamlit_manual_review import manual_review_store_or_stop, start_corrected_item_search
from ..streamlit_shared import ARTIFACTS_DIR


def render_saved_decisions() -> None:
    """Render a table of previously corrected items and allow re-searching."""
    st.divider()
    st.subheader("Saved Corrections (Manual Review Store)")
    store = manual_review_store_or_stop()
    decisions = store.list_decisions()
    if not decisions:
        st.info("No saved decisions found.")
        return
    display_df = _prepare_saved_decisions_display(decisions, store)
    if display_df is None:
        return
    _render_source_history(store)
    _render_latest_approved_correction_report(decisions)
    _render_saved_actions(display_df, decisions)


# ============ Display Preparation ============

def _prepare_saved_decisions_display(decisions, store):
    """Prepare and validate display DataFrame."""
    df = pd.DataFrame([_decision_row(d) for d in decisions])
    selected_columns = _select_saved_columns(df)
    if not selected_columns:
        st.warning("Please select at least one column.")
        return None
    editor_columns = _build_editor_columns(selected_columns)
    return _prepare_display_df(df, editor_columns, selected_columns)


def _select_saved_columns(df):
    """Select columns to display."""
    all_columns = list(df.columns)
    default_columns = [
        "item_code", "item_name", "run_date", "decision", "manual_decision",
        "matching_source", "matching_source_label",
        "supplier_scope_key", "last_rebind_status",
        "correct_product_name", "correct_product_name_ar"
    ]
    default_columns = [col for col in default_columns if col in all_columns]
    return st.multiselect(
        "Select columns to display and download:",
        options=all_columns,
        default=default_columns,
        key="saved_decisions_columns_v2",
    )


def _build_editor_columns(selected_columns):
    """Build editor columns with identity columns first."""
    # Supplier scope is part of the persistent identity.  Keep it in the
    # editor even when the user customises the visible business columns so a
    # deletion or approval can never fall back to item-only behaviour.
    identity_columns = [
        "item_code", "item_name", "matching_source", "matching_source_label",
        "excel_target_key",
    ]
    return identity_columns + [c for c in selected_columns if c not in identity_columns]


def _prepare_display_df(df, editor_columns, selected_columns):
    """Prepare and sort display dataframe."""
    sort_col, is_ascending = _get_sort_preferences(selected_columns)
    display_df = df[editor_columns].copy()
    display_df.insert(0, "تحديد (Select)", False)
    if sort_col:
        # Keep the store's newest-first order for rows sharing the same run
        # timestamp (for example, decisions saved in one batch).
        sort_key = None
        if sort_col == "run_date":
            # Legacy imports use values such as ``csv_import`` instead of a
            # timestamp.  Treat those values as unknown dates so they stay
            # below real timestamped runs when sorting newest first.
            sort_key = lambda values: pd.to_datetime(
                values.astype("string"),
                format="%Y%m%d_%H%M",
                errors="coerce",
            )
        display_df = display_df.sort_values(
            by=sort_col,
            ascending=is_ascending,
            kind="stable",
            key=sort_key,
            na_position="last",
        )
    return display_df


def _default_sort_preferences(selected_columns):
    """Return the default sort column and direction for saved corrections."""
    if "run_date" in selected_columns:
        return "run_date", False
    if "item_name" in selected_columns:
        return "item_name", True
    if selected_columns:
        return selected_columns[0], True
    return None, True


def _get_sort_preferences(selected_columns):
    """Get user sort column and order preferences."""
    col_sort, col_order = st.columns(2)
    default_sort_col, default_ascending = _default_sort_preferences(selected_columns)
    with col_sort:
        default_idx = (
            selected_columns.index(default_sort_col)
            if default_sort_col in selected_columns else 0
        )
        sort_col = st.selectbox(
            "ترتيب حسب (Sort By):",
            options=selected_columns,
            index=default_idx,
            key="saved_decisions_sort_column_v2",
        )
    with col_order:
        sort_asc = st.radio(
            "ترتيب (Order):",
            options=["تصاعدي (Ascending)", "تنازلي (Descending)"],
            index=0 if default_ascending else 1,
            horizontal=True,
            key="saved_decisions_sort_order_v2",
        )
    is_ascending = sort_asc == "تصاعدي (Ascending)"
    return sort_col, is_ascending


def _decision_row(d) -> dict:
    """Return a backward-compatible, provenance-rich display row."""
    target_key = getattr(d, "excel_target_key", "")
    source = getattr(d, "matching_source", "") or getattr(d, "source_kind", "")
    if not source and target_key:
        # Decisions written before the explicit source migration can still be
        # identified safely from their target scope.
        source = "excel_target"
    return {
        "item_code": d.item_code,
        "item_name": d.item_name,
        "run_date": d.run_id,
        "decision": d.manual_decision,
        "manual_decision": d.manual_decision,
        "matching_source": source,
        "matching_source_label": getattr(d, "matching_source_label", "") or "",
        "identity_evidence_kind": getattr(d, "identity_evidence_kind", "") or "",
        "identity_evidence": getattr(d, "identity_evidence", "") or "",
        "correct_store_product_id": d.correct_store_product_id,
        "correct_product_name": getattr(d, "correct_product_name", ""),
        "correct_product_name_ar": getattr(d, "correct_product_name_ar", ""),
        "correct_query": d.correct_query,
        "run_id": d.run_id,
        "excel_target_key": target_key,
        "excel_target_source_file": getattr(d, "excel_target_source_file", "") or "",
        "supplier_scope_key": getattr(d, "supplier_scope_key", "") or "",
        "last_rebind_status": getattr(d, "last_rebind_status", "") or "",
        "approved": d.approved,
    }


# ============ Action Handling ============

def _render_saved_actions(display_df, decisions):
    """Render editor, actions, and download/search buttons."""
    _show_saved_instructions()
    edited_df = _render_saved_editor(display_df)
    _handle_saved_modifications(display_df, edited_df)
    _render_download_and_search(display_df, decisions)


def _render_source_history(store) -> None:
    """Show catalog files previously observed for logical supplier decisions."""
    history = store.list_all_source_history()
    if not history:
        return
    with st.expander("Supplier catalog history", expanded=False):
        st.dataframe(
            pd.DataFrame([dataclasses.asdict(row) for row in history]),
            hide_index=True,
            width="stretch",
        )


# ============ Approved-correction audit (read-only) ============

_REPORT_FILE_PREFIX = "approved_correction_report"
_SAFE_FINDING_FIELDS = (
    "item_code",
    "item_name",
    "target_key",
    "row_key",
    "approval_run_id",
    "approval_status",
    "counterfactual_status",
    "root_cause",
    "original_reason",
    "counterfactual_reason",
    "final_reason",
    "compatibility_status",
    "candidate_method",
    "candidate_count_total",
    "decision_source",
    "match_origin",
    "excel_target_source_row",
    "excel_target_source_file",
)
_SAFE_RECOMMENDATION_FIELDS = (
    "root_cause",
    "evidence_count",
    "sample_item_keys",
    "requires_human_approval",
)


def _report_mapping(report) -> dict:
    """Return a mapping for either JSON data or report dataclasses.

    The UI intentionally accepts the serialized report contract rather than
    importing the analyzer.  This keeps the page read-only and lets reports
    generated by a different process remain inspectable during upgrades.
    """
    if isinstance(report, Mapping):
        return dict(report)
    if dataclasses.is_dataclass(report):
        return dataclasses.asdict(report)
    if hasattr(report, "to_dict"):
        value = report.to_dict()
        return dict(value) if isinstance(value, Mapping) else {}
    return {}


def _report_findings(report) -> list[dict]:
    """Normalize report findings into plain mappings."""
    findings = _report_mapping(report).get("findings", ())
    rows = []
    for finding in findings or ():
        row = _report_mapping(finding)
        if row:
            rows.append(row)
    return rows


def _report_root_cause_counts(report) -> dict[str, int]:
    """Return deterministic root-cause counts from a report contract."""
    payload = _report_mapping(report)
    counts = payload.get("counts_by_root_cause")
    if not isinstance(counts, Mapping):
        nested_counts = payload.get("counts")
        if isinstance(nested_counts, Mapping):
            counts = nested_counts.get("by_root_cause") or nested_counts.get(
                "counts_by_root_cause"
            )
    if isinstance(counts, Mapping):
        result = {}
        for root_cause, count in counts.items():
            try:
                result[str(root_cause)] = int(count)
            except (TypeError, ValueError):
                continue
        return dict(sorted(result.items(), key=lambda pair: (-pair[1], pair[0])))

    derived: dict[str, int] = {}
    for finding in _report_findings(payload):
        root_cause = str(finding.get("root_cause", "") or "unknown")
        derived[root_cause] = derived.get(root_cause, 0) + 1
    return dict(sorted(derived.items(), key=lambda pair: (-pair[1], pair[0])))


def _safe_report_finding(finding: Mapping) -> dict:
    """Project one finding to fields safe for browser display.

    In particular, arbitrary report metadata (including database paths) is
    never forwarded to Streamlit.  The source workbook is reduced to a file
    name because its absolute path is operational detail, not audit evidence.
    """
    row = {}
    for field in _SAFE_FINDING_FIELDS:
        value = finding.get(field, "")
        if field == "excel_target_source_file":
            value = _source_file_name(value)
        elif field == "candidate_count_total":
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = 0
        elif isinstance(value, (list, tuple, set)):
            value = ", ".join(str(part) for part in value)
        elif value is None:
            value = ""
        row[field] = value
    return row


def _source_file_name(value) -> str:
    """Strip directories from a report source-file value for display."""
    text = str(value or "")
    if not text:
        return ""
    # ``Path`` follows the host platform; accepting both separators keeps
    # reports generated on Windows and Linux safe when viewed elsewhere.
    basename = text.replace("\\", "/").rsplit("/", 1)[-1]
    # The report contract expects a workbook source.  Refuse unrelated path
    # values defensively so an accidental database/config path is not exposed
    # in the browser payload.
    if not basename.lower().endswith((".xlsx", ".xlsm", ".xls", ".csv", ".tsv")):
        return ""
    return basename


def _is_stale_finding(finding: Mapping) -> bool:
    """Return whether a finding represents stale/invalid approval provenance."""
    status = str(finding.get("approval_status", "") or "").strip().lower()
    root_cause = str(finding.get("root_cause", "") or "").strip().lower()
    return status in {"stale", "invalid"} or root_cause in {
        "stale",
        "stale_row_key",
        "legacy_invalid",
        "approval_outside_current_input",
    }


def _safe_report_recommendation(recommendation: Mapping) -> dict:
    """Project recommendation evidence without exposing arbitrary metadata."""
    row = {}
    for field in _SAFE_RECOMMENDATION_FIELDS:
        value = recommendation.get(field, "")
        if field == "sample_item_keys" and isinstance(value, (list, tuple, set)):
            value = ", ".join(str(part) for part in value)
        row[field] = value
    return row


def _approved_correction_report_view_model(report, *, sample_limit: int = 20) -> dict:
    """Build the read-only view model used by the Saved Corrections page."""
    payload = _report_mapping(report)
    findings = _report_findings(payload)
    safe_findings = [_safe_report_finding(finding) for finding in findings]
    stale = [
        _safe_report_finding(finding)
        for finding in findings
        if _is_stale_finding(finding)
    ]
    recommendations = payload.get("recommendations", ())
    safe_recommendations = [
        _safe_report_recommendation(_report_mapping(recommendation))
        for recommendation in recommendations or ()
    ]
    counts = payload.get("counts", {})
    return {
        "schema_version": str(payload.get("schema_version", "") or ""),
        "generated_at": str(payload.get("generated_at", "") or ""),
        "target_catalog_fingerprint": str(
            payload.get("target_catalog_fingerprint", "") or ""
        )[:16],
        "counts": dict(counts) if isinstance(counts, Mapping) else {},
        "root_cause_counts": _report_root_cause_counts(payload),
        "samples": safe_findings[:sample_limit],
        "stale_approvals": stale[:sample_limit],
        "recommendations": safe_recommendations[:sample_limit],
    }


def _render_approved_correction_report(report) -> None:
    """Render one approved-correction report without any mutation controls."""
    view = _approved_correction_report_view_model(report)
    with st.expander("Approved correction audit (read-only)", expanded=False):
        metadata = []
        if view["schema_version"]:
            metadata.append(f"Schema: {view['schema_version']}")
        if view["generated_at"]:
            metadata.append(f"Generated: {view['generated_at']}")
        if view["target_catalog_fingerprint"]:
            metadata.append(
                f"Catalog fingerprint: {view['target_catalog_fingerprint']}"
            )
        if metadata:
            st.caption(" · ".join(metadata))

        counts = view["counts"]
        for name in (
            "automatic_verified",
            "approved_manual_override",
            "saved_auto_matched",
            "stale_or_invalid",
            "approval_outside_current_input",
        ):
            if name in counts:
                st.metric(name.replace("_", " ").title(), counts[name])

        st.subheader("Root-cause counts")
        root_cause_counts = view["root_cause_counts"]
        if root_cause_counts:
            for root_cause, count in root_cause_counts.items():
                st.metric(f"Root cause: {root_cause}", count)
        else:
            st.info("No root-cause findings in this report.")

        if view["stale_approvals"]:
            st.subheader("Stale or invalid approvals")
            st.dataframe(
                pd.DataFrame(view["stale_approvals"]),
                hide_index=True,
                width="stretch",
            )

        if view["samples"]:
            st.subheader("Finding samples")
            st.dataframe(
                pd.DataFrame(view["samples"]),
                hide_index=True,
                width="stretch",
            )

        if view["recommendations"]:
            st.subheader("Recommendation evidence")
            st.dataframe(
                pd.DataFrame(view["recommendations"]),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Recommendations are evidence for human review only; this page "
                "does not apply matching rules."
            )


def _latest_approved_correction_report(
    artifacts_dir: Path, target_key: str
) -> Path | None:
    """Return the newest report for one target, if one exists."""
    target_dir = Path(artifacts_dir) / "excel-target" / str(target_key)
    if not target_dir.is_dir():
        return None
    candidates = sorted(
        target_dir.rglob(f"{_REPORT_FILE_PREFIX}*.json"),
        key=lambda path: (path.parent.name, path.stat().st_mtime_ns, str(path)),
    )
    return candidates[-1] if candidates else None


def _render_latest_approved_correction_report(decisions) -> None:
    """Select and render the newest report for saved Excel-target approvals."""
    target_keys = sorted(
        {
            str(getattr(decision, "excel_target_key", "") or "")
            for decision in decisions
            if str(getattr(decision, "excel_target_key", "") or "")
            and str(getattr(decision, "matching_source", "") or "")
            .strip()
            .lower()
            .replace("_", "-")
            == "excel-target"
        }
    )
    reports = {
        target_key: _latest_approved_correction_report(ARTIFACTS_DIR, target_key)
        for target_key in target_keys
    }
    reports = {target_key: path for target_key, path in reports.items() if path}
    if not reports:
        return

    if len(reports) > 1:
        target_key = st.selectbox(
            "Excel target audit report",
            options=list(reports),
            key="saved_correction_report_target",
        )
    else:
        target_key = next(iter(reports))
    report_path = reports.get(target_key)
    if report_path is None:
        return
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        st.warning("The latest approved-correction audit report could not be read.")
        return
    _render_approved_correction_report(report)


def _show_saved_instructions():
    """Show instruction messages for saved decisions."""
    st.info(
        "💡 You can delete rows directly from the table below. Select a row "
        "and press Delete (or click the trash icon) to revoke the decision "
        "and return the item to local matching."
    )
    st.info(
        "💡 You can check the 'تحديد (Select)' box to select 'auto_matched' "
        "items and convert them to 'approved_match' using the button below."
    )


def _render_saved_editor(display_df):
    """Render the data editor for saved decisions."""
    return st.data_editor(
        display_df,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        key="saved_decisions_editor_v2",
    )


def _handle_saved_modifications(display_df, edited_df):
    """Handle approval conversion and deletion."""
    store = manual_review_store_or_stop()
    _handle_approval_conversion(edited_df, store)
    _handle_deletion(display_df, edited_df, store)


def _render_download_and_search(display_df, decisions):
    """Render download button and search trigger."""
    download_df = display_df.drop(columns=["تحديد (Select)"], errors="ignore")
    csv_data = download_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Download Corrected Items (CSV)", data=csv_data,
        file_name="saved_corrected_items.csv", mime="text/csv"
    )
    if st.button("Search Corrected Items (Run Match-Only)"):
        _trigger_search(decisions)


def _trigger_search(decisions: list) -> None:
    valid_status = ("needs_correction", "approved_match", "auto_matched")
    fake_rows = [
        {"item_code": d.item_code, "item_name": d.item_name}
        for d in decisions if d.manual_decision in valid_status
    ]
    dummy_run_dir = ARTIFACTS_DIR / "order" / "manual_research"
    dummy_run_dir.mkdir(parents=True, exist_ok=True)
    start_corrected_item_search(fake_rows, dummy_run_dir, st)
    st.success("Started corrected item search!")


def _handle_deletion(display_df, edited_df, store):
    """Handle deletion of selected items."""
    if len(edited_df) >= len(display_df):
        return
    deleted_pairs = deleted_identity_pairs(display_df, edited_df)
    if deleted_pairs:
        if st.button("🗑️ Confirm Deletion of Selected Items"):
            for code, name, source, source_label, target_key in deleted_pairs:
                kwargs = {"matching_source": source}
                if source.replace("_", "-") == "excel-target" and target_key:
                    kwargs["excel_target_key"] = target_key
                else:
                    kwargs["matching_source_label"] = source_label
                store.delete(code, name, **kwargs)
            st.success(
                f"Successfully deleted {len(deleted_pairs)} items from saved corrections!"
            )
            st.rerun()


def deleted_identity_pairs(original_df, edited_df) -> list[tuple[str, str, str, str, str]]:
    """Return exact item-and-supplier identities removed from the table."""
    columns = [
        "item_code", "item_name", "matching_source", "matching_source_label",
        "excel_target_key",
    ]
    original = set(original_df.reindex(columns=columns, fill_value="").itertuples(index=False, name=None))
    edited = set(edited_df.reindex(columns=columns, fill_value="").itertuples(index=False, name=None))
    return sorted(original - edited)


# ============ Approval Conversion ============

def _handle_approval_conversion(edited_df, store):
    """Handle conversion from auto_matched to approved_match."""
    selected_auto_matched = edited_df[
        (edited_df["تحديد (Select)"] == True) &
        (edited_df["decision"] == "auto_matched")
    ]
    if selected_auto_matched.empty:
        return
    _render_conversion_button(selected_auto_matched, store)


def _render_conversion_button(selected_auto_matched, store):
    """Render conversion button and handle conversion."""
    button_label = (
        f"✔️ تحويل {len(selected_auto_matched)} صنف محدد من "
        f"auto_matched إلى approved_match"
    )
    if st.button(button_label, type="primary"):
        _convert_to_approved(selected_auto_matched, store)


def _convert_to_approved(selected_auto_matched, store):
    """Convert selected auto_matched items to approved_match."""
    for _, row in selected_auto_matched.iterrows():
        source = str(row.get("matching_source", "") or "")
        target_key = str(row.get("excel_target_key", "") or "")
        lookup_kwargs = {"matching_source": source}
        if source.replace("_", "-") == "excel-target" and target_key:
            lookup_kwargs["excel_target_key"] = target_key
        else:
            lookup_kwargs["matching_source_label"] = str(
                row.get("matching_source_label", "") or ""
            )
        decision_obj = store.lookup(
            str(row["item_code"]), str(row["item_name"]), **lookup_kwargs
        )
        if decision_obj and decision_obj.manual_decision == "auto_matched":
            new_decision = dataclasses.replace(
                decision_obj, manual_decision="approved_match"
            )
            store.upsert(new_decision)
    st.success(
        f"Successfully converted {len(selected_auto_matched)} items to approved_match!"
    )
    st.rerun()


__all__ = [
    "render_saved_decisions",
    "deleted_identity_pairs",
    "_decision_row",
]
