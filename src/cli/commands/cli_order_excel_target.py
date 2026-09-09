"""Excel target order item flow — match-only against in-memory catalogs."""

from __future__ import annotations

import csv
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Iterable

from src.core.artifact_run import artifact_run
from src.core.config.config_models import AppConfig
from src.core.excel_target import (
    TargetProduct,
    ExcelTargetMatcher,
    load_target_catalog_from_excel,
    match_item_against_all_targets,
    first_accepted_match,
)
from src.core.excel_target.product_attributes import validate_product_compatibility
from src.core.manual_review.manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)
from src.core.database.order_runs_keys import order_run_item_key
from src.core.matching.candidate_identity import candidate_store_product_id
from src.core.utils.excel import Item
from src.tawreed.matching.tawreed_match_only import MATCH_ONLY_SUMMARY_LABEL


logger = logging.getLogger(__name__)


def selected_excel_target_configs(
    app_config: AppConfig, args
) -> list[tuple[str, list[Path]]]:
    """Resolve the list of Excel targets the run should match against.

    Resolution priority:
    1. ``--excel-target <key>`` (single target by config key)
    2. ``--all-excel-targets`` (every enabled target)
    3. ``--excel-target-path <key>=<path>[,...]`` (override one or more paths)

    Each resolved entry is ``(target_key, [catalog_xlsx_paths])``. The list
    holds a single path for a vanilla ``--excel-target`` run, or several
    paths when the operator picked multiple files in the GUI.
    """
    enabled = app_config.enabled_excel_targets()
    if not enabled:
        return []

    target_path_overrides: dict[str, list[str]] = {}
    raw_overrides = getattr(args, "excel_target_path", None) or []
    if isinstance(raw_overrides, str):
        raw_overrides = [raw_overrides]
    for raw_override in raw_overrides:
        for entry in raw_override.split(","):
            entry = entry.strip()
            if not entry or "=" not in entry:
                continue
            key, _, path = entry.partition("=")
            target_path_overrides.setdefault(key.strip(), []).append(path.strip())

    if getattr(args, "excel_target", None):
        key = str(args.excel_target)
        if key not in enabled:
            available = ", ".join(enabled.keys())
            raise ValueError(
                f"Unknown excel-target '{key}'. Available: {available}"
            )
        targets = [(key, enabled[key])]
    elif getattr(args, "all_excel_targets", False):
        targets = list(enabled.items())
    else:
        return []

    default_dir = Path("data/input/excel target")
    resolved: list[tuple[str, list[Path]]] = []
    for target_key, target_cfg in targets:
        if target_key in target_path_overrides:
            xlsx_paths = [Path(p) for p in target_path_overrides[target_key]]
        else:
            xlsx_paths = [default_dir / f"{target_key}.xlsx"]
        resolved.append((target_key, xlsx_paths))
    return resolved


def load_target_catalogs(
    selected: list[tuple[str, list[Path]]], app_config: AppConfig
) -> dict[str, list[TargetProduct]]:
    """Read every resolved Excel target catalog into memory.

    When a target key resolves to several paths (e.g. the operator
    selected multiple existing files in the GUI), the parsed catalogs are
    concatenated into a single in-memory list. Each product carries the
    ``source_file`` label of the file it came from so the summary CSV can
    keep the provenance.
    """
    catalogs: dict[str, list[TargetProduct]] = {}
    for target_key, xlsx_paths in selected:
        if target_key not in app_config.excel_targets:
            continue
        target_cfg = app_config.excel_targets[target_key]
        merged: list[TargetProduct] = []
        for xlsx_path in xlsx_paths:
            try:
                parsed = load_target_catalog_from_excel(
                    xlsx_path, target_cfg, source_file=xlsx_path.name
                )
            except FileNotFoundError as error:
                logger.warning(
                    "excel target catalog missing",
                    extra={"target": target_key, "path": str(xlsx_path)},
                )
                logger.debug("excel target load failure: %s", error)
                continue
            merged.extend(parsed)
        catalogs[target_key] = merged
    return catalogs


def run_excel_target_match_only(
    app_config: AppConfig,
    target_key: str,
    items: Iterable[Item],
    catalog: list[TargetProduct],
    summary_path: Path,
    run_key: str | None = None,
    run_id: str | None = None,
    allow_live_translation: bool = False,
) -> dict[str, int]:
    """Run match-only for one Excel target and persist a summary CSV.

    Returns counters ``{"processed": N, "matched": M, "flagged": F}`` for the
    target. Each row mirrors the Tawreed match-only summary shape so the
    downstream tools (``render_fresh_run_analysis``, ``Run DB``) work without
    changes. When the catalog was built from several files the
    ``source_file`` column records which file the matched row came from.

    When ``run_key`` is provided, each item is also persisted to the
    ``order_runs.db`` with ``source_kind='excel-target'`` and
    ``source_label='<target_key>[@<source_file>]'`` so the Run DB tab can
    distinguish Excel-target matches from Tawreed ones. The matching
    product is also written to ``run_item_stores`` with
    ``source='excel_target'`` so the per-item offering-store expander
    in the Run Results tab shows the Excel candidate alongside any
    Tawreed rows.
    """
    matched = flagged = manual_review_count = 0
    items_list = list(items)
    matcher = ExcelTargetMatcher(
        target_key,
        catalog,
        allow_live_translation=allow_live_translation,
    )
    deadline = time.monotonic() + 300
    timed_out = False
    db_persist = _build_db_persister(app_config, run_key, target_key)
    provided_run_id = run_id or (
        _extract_run_id(run_key) if run_key else None
    )
    with artifact_run("excel-target", target_key, run_id=provided_run_id) as run:
        _ensure_run_record(app_config, run_key, run, target_key)
        target_summary = (
            run.directory / f"{MATCH_ONLY_SUMMARY_LABEL}_{target_key}.csv"
        )
        trace_path = run.directory / f"{MATCH_ONLY_SUMMARY_LABEL}_{target_key}.jsonl"
        review_csv_path = run.directory / f"manual_review_excel-target_{target_key}.csv"
        review_candidates_path = (
            run.directory / f"manual_review_candidates_excel-target_{target_key}.jsonl"
        )
        # Write to a temp file and atomically replace at the end so a
        # run killed mid-loop leaves no zero-byte summary artifact.
        tmp_summary = target_summary.with_suffix(".csv.tmp")
        stale_tmp = target_summary.with_suffix(".tmp")
        for leftover in (stale_tmp,):
            try:
                leftover.unlink()
            except OSError:
                pass
        with tmp_summary.open("w", newline="", encoding="utf-8") as fh, trace_path.open(
            "w", encoding="utf-8"
        ) as trace:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "target_kind",
                    "target_key",
                    "source_file",
                    "item_code",
                    "item_name",
                    "matched_name",
                    "matched_price",
                    "matched_discount",
                    "status",
                    "score",
                    "final_reason",
                    "identity_evidence_kind",
                    "identity_evidence",
                    "compatibility_status",
                    "compatibility_rejection",
                    "match_elapsed_ms",
                    "candidate_source_file",
                    "candidate_count_total",
                    "candidate_count",
                    "manual_review_required",
                    "manual_review_category",
                    "matching_source",
                    "matching_source_label",
                ]
            )
            for item in items_list:
                if time.monotonic() > deadline:
                    timed_out = True
                    break
                item_started = time.perf_counter()
                result = matcher.match(item, app_config.matching)
                elapsed_ms = round((time.perf_counter() - item_started) * 1000, 2)
                if result is None:
                    writer.writerow(
                        [
                            "excel-target",
                            target_key,
                            "",
                            item.code,
                            item.name,
                            "",
                            "",
                            "",
                            "no-results",
                            "0",
                            "no catalog",
                            "", "", "rejected", "no catalog", elapsed_ms, "",
                            0, 0, False, "identity_absent", "excel-target", target_key,
                        ]
                    )
                    trace.write(json.dumps({
                        "item_code": item.code,
                        "item_name": item.name,
                        "status": "no-results",
                        "reason": "no catalog",
                        "identity_evidence_kind": "",
                        "identity_evidence": "",
                        "compatibility_status": "rejected",
                        "compatibility_rejection": "no catalog",
                        "match_elapsed_ms": elapsed_ms,
                        "catalog_size": 0,
                        "candidate_count": 0,
                        "candidate_count_total": 0,
                        "manual_review_required": False,
                        "manual_review_category": "identity_absent",
                        "matching_source": "excel-target",
                        "matching_source_label": target_key,
                    }, ensure_ascii=False) + "\n")
                    db_persist(
                        item,
                        status="no-results",
                        score=0.0,
                        reason="no catalog",
                        source_file="",
                        candidate_count=0,
                        manual_review_required=False,
                    )
                    continue
                decision = result.decision
                best = decision.best_match
                if best is None:
                    identified = matcher.identity_index.identify(item.name)
                    identity_kinds = ";".join(
                        dict.fromkeys(candidate.evidence.kind for candidate in identified)
                    )
                    identity_details = "; ".join(
                        dict.fromkeys(candidate.evidence.detail for candidate in identified)
                    )
                    compatibility_rejection = decision.final_reason
                    if identified and not compatibility_rejection:
                        compatibility_rejection = validate_product_compatibility(
                            item.name, identified[0].product.name_ar
                        ).rejection_reason
                    score = (
                        f"{decision.diagnostics[0].score:.2f}"
                        if decision.diagnostics
                        else "0"
                    )
                    review_limit = _review_candidate_limit(app_config)
                    all_review_candidates = tuple(result.review_candidates)
                    review_candidates = all_review_candidates[:review_limit]
                    candidate_count_total = len(all_review_candidates)
                    candidate_count = len(review_candidates)
                    review_required = candidate_count_total > 0
                    review_category = (
                        "excel_target_candidate_available" if review_required
                        else _excel_target_no_candidate_category(bool(identified))
                    )
                    candidate_source_file = ";".join(
                        dict.fromkeys(
                            candidate.product.source_file
                            for candidate in review_candidates
                            if candidate.product.source_file
                        )
                    )
                    candidate_evidence_kinds = ";".join(
                        dict.fromkeys(
                            candidate.identity_evidence_kind
                            for candidate in review_candidates
                            if candidate.identity_evidence_kind
                        )
                    )
                    candidate_evidence_details = "; ".join(
                        dict.fromkeys(
                            candidate.identity_evidence_detail
                            for candidate in review_candidates
                            if candidate.identity_evidence_detail
                        )
                    )
                    reported_identity_kinds = _merge_evidence_values(
                        identity_kinds, candidate_evidence_kinds
                    )
                    reported_identity_details = _merge_evidence_values(
                        identity_details, candidate_evidence_details, separator="; "
                    )
                    if review_required:
                        _append_excel_target_review_artifacts(
                            review_csv_path,
                            review_candidates_path,
                            item,
                            review_candidates,
                            reason=decision.final_reason,
                            identity_evidence_kind=candidate_evidence_kinds or identity_kinds,
                            identity_evidence=candidate_evidence_details or identity_details,
                            compatibility_rejection=compatibility_rejection,
                            candidate_count_total=candidate_count_total,
                        )
                        manual_review_count += 1
                    writer.writerow(
                        [
                            "excel-target",
                            target_key,
                            "",
                            item.code,
                            item.name,
                            "",
                            "",
                            "",
                            "no-results",
                            score,
                            decision.final_reason,
                            reported_identity_kinds,
                            reported_identity_details,
                            "rejected",
                            compatibility_rejection,
                            elapsed_ms,
                            candidate_source_file,
                            candidate_count_total,
                            candidate_count,
                            review_required,
                            review_category,
                            "excel-target",
                            _excel_target_source_label(target_key, candidate_source_file),
                        ]
                    )
                    trace.write(json.dumps({
                        "item_code": item.code,
                        "item_name": item.name,
                        "status": "no-results",
                        "reason": decision.final_reason,
                        "identity_evidence_kind": reported_identity_kinds,
                        "identity_evidence": reported_identity_details,
                        "compatibility_status": "rejected",
                        "compatibility_rejection": compatibility_rejection,
                        "match_elapsed_ms": elapsed_ms,
                        "catalog_size": len(catalog),
                        "candidate_count": candidate_count,
                        "candidate_count_total": candidate_count_total,
                        "manual_review_required": review_required,
                        "manual_review_category": review_category,
                        "candidate_source_file": candidate_source_file,
                        "matching_source": "excel-target",
                        "matching_source_label": _excel_target_source_label(
                            target_key, candidate_source_file
                        ),
                    }, ensure_ascii=False) + "\n")
                    flagged += 1
                    db_persist(
                        item,
                        status="no-results",
                        score=float(score or 0),
                        reason=decision.final_reason,
                        source_file="",
                        best=None,
                        candidate_count=candidate_count,
                        candidate_count_total=candidate_count_total,
                        manual_review_required=review_required,
                        manual_review_category=review_category,
                    )
                    continue
                source_file = str(best.data.get("excelTargetSourceFile", ""))
                writer.writerow(
                    [
                        "excel-target",
                        target_key,
                        source_file,
                        item.code,
                        item.name,
                        str(best.data.get("productName", best.data.get("productNameEn", ""))),
                        str(best.data.get("salePrice", "")),
                        str(best.data.get("discountPercent", "")),
                        "matched-only",
                        f"{best.score:.2f}",
                        decision.final_reason,
                        str(best.data.get("identity_evidence_kind", "")),
                        str(best.data.get("identity_evidence", "")),
                        str(best.data.get("compatibility_status", "")),
                        str(best.data.get("compatibility_rejection", "")),
                        str(best.data.get("match_elapsed_ms", "")),
                        source_file,
                        0,
                        0,
                        False,
                        "",
                        "excel-target",
                        _excel_target_source_label(target_key, source_file),
                    ]
                )
                trace.write(json.dumps({
                    "item_code": item.code,
                    "item_name": item.name,
                    "status": "matched-only",
                    "reason": decision.final_reason,
                    "identity_evidence_kind": best.data.get("identity_evidence_kind", ""),
                    "identity_evidence": best.data.get("identity_evidence", ""),
                    "compatibility_status": best.data.get("compatibility_status", ""),
                    "match_elapsed_ms": best.data.get("match_elapsed_ms", ""),
                    "catalog_size": len(catalog),
                    "candidate_count": 0,
                    "candidate_count_total": 0,
                    "manual_review_required": False,
                    "manual_review_category": "identity_compatible",
                    "matching_source": "excel-target",
                    "matching_source_label": _excel_target_source_label(
                        target_key, source_file
                    ),
                }, ensure_ascii=False) + "\n")
                matched += 1
                db_persist(
                    item,
                    status="matched-only",
                    score=best.score,
                    reason=decision.final_reason,
                    source_file=source_file,
                    best=best.data,
                    matched_name=str(best.data.get("productName", best.data.get("productNameEn", ""))),
                    matched_price=str(best.data.get("salePrice", "")),
                    matched_discount=str(best.data.get("discountPercent", "")),
                    candidate_count=0,
                    candidate_count_total=0,
                    manual_review_required=False,
                    manual_review_category="identity_compatible",
                )
                _auto_save_excel_target_match(
                    app_config,
                    item,
                    best.data,
                    target_key=target_key,
                    source_file=source_file,
                    run_id=run.run_id,
                )
        os.replace(tmp_summary, target_summary)
        try:
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_summary, summary_path)
        except OSError:
            logger.debug(
                "could not mirror excel-target summary", extra={"path": str(summary_path)}
            )

        if timed_out:
            raise TimeoutError("Excel-target match-only exceeded the 300-second safety limit")

    _finish_run_record(app_config, run_key)
    from src.core.normalization.translation import provider_status

    status = provider_status()
    if status["quota_dead"]:
        logger.warning(
            "live translation was DISABLED during this run (monthly quota exhausted) "
            "— matches relied on the translation cache only"
        )
    elif status["breaker_open"] or status["consecutive_failures"]:
        logger.warning(
            "translation provider state at run end: %s", status
        )
    return {
        "processed": len(items_list),
        "matched": matched,
        "flagged": flagged,
        "manual_review": manual_review_count,
    }


def run_excel_target_match_only_multi(
    app_config: AppConfig,
    selected: list[tuple[str, list[Path]]],
    catalogs: dict[str, list[TargetProduct]],
    items: Iterable[Item],
    summary_path: Path,
    run_key: str | None = None,
    run_id: str | None = None,
) -> dict[str, dict[str, int]]:
    """Run match-only across every Excel target, returning per-target totals.

    ``run_id`` is the bare timestamp half of ``run_key`` (``<profile>/<run_id>``).
    Passing it explicitly avoids the artifact directory mismatch that
    happens when the excel-target flow derives its own minute-stamp from
    ``unique_run_id("excel-target", target_key)`` (which usually differs by
    a tick from the Tawreed flow's ``unique_run_id("order", profile_key)``).
    """
    items_list = list(items)
    totals: dict[str, dict[str, int]] = {}
    for target_key, _xlsx_paths in selected:
        catalog = catalogs.get(target_key, [])
        totals[target_key] = run_excel_target_match_only(
            app_config,
            target_key,
            items_list,
            catalog,
            summary_path=summary_path.with_name(
                f"{summary_path.stem}_{target_key}{summary_path.suffix}"
            ),
            run_key=run_key,
            run_id=run_id,
            allow_live_translation=True,
        )
    return totals


def _review_candidate_limit(app_config: AppConfig) -> int:
    """Return the configured number of options persisted for human review."""
    value = getattr(
        getattr(app_config, "matching", None),
        "manual_review_save_candidate_limit",
        5,
    )
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 5


def _excel_target_source_label(target_key: str, source_file: str = "") -> str:
    """Build the same source label used by Run DB and Saved Corrections."""
    return f"{target_key}@{source_file}" if source_file else str(target_key or "")


def _excel_target_no_candidate_category(has_identity: bool) -> str:
    """Classify a blocked target row that has no review candidate."""
    return "identity_variant_rejected" if has_identity else "identity_absent"


def _merge_evidence_values(
    primary: str, secondary: str, *, separator: str = ";"
) -> str:
    """Combine evidence labels while preserving their original order."""
    return separator.join(
        dict.fromkeys(value for value in (primary, secondary) if value)
    )


def _append_excel_target_review_artifacts(
    review_csv_path: Path,
    candidates_path: Path,
    item: Item,
    candidates,
    *,
    reason: str,
    identity_evidence_kind: str,
    identity_evidence: str,
    compatibility_rejection: str,
    candidate_count_total: int,
) -> None:
    """Persist one Baraka review row and its target-only candidates."""
    if not candidates:
        return
    source_files = ";".join(
        dict.fromkeys(
            candidate.product.source_file
            for candidate in candidates
            if candidate.product.source_file
        )
    )
    source_label = _excel_target_source_label(
        candidates[0].target_key,
        source_files,
    )
    review_csv_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not review_csv_path.exists() or review_csv_path.stat().st_size == 0
    with review_csv_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "item_code", "item_name", "status", "manual_review_required",
                "manual_review_category", "candidate_count", "candidate_count_total",
                "candidate_count_saved", "matching_source",
                "matching_source_label", "target_key", "source_file",
                "identity_evidence_kind", "identity_evidence",
                "compatibility_status", "candidate_compatibility_status",
                "compatibility_rejection", "reason",
            ],
        )
        if needs_header:
            writer.writeheader()
        writer.writerow(
            {
                "item_code": item.code,
                "item_name": item.name,
                "status": "no-results",
                "manual_review_required": True,
                "manual_review_category": "excel_target_candidate_available",
                "candidate_count": len(candidates),
                "candidate_count_total": candidate_count_total,
                "candidate_count_saved": len(candidates),
                "matching_source": "excel-target",
                "matching_source_label": source_label,
                "target_key": candidates[0].target_key,
                "source_file": source_files,
                "identity_evidence_kind": identity_evidence_kind,
                "identity_evidence": identity_evidence,
                "compatibility_status": "rejected",
                "candidate_compatibility_status": _candidate_compatibility_status(candidates),
                "compatibility_rejection": compatibility_rejection,
                "reason": reason,
            }
        )

    payload = {
        "item_key": order_run_item_key(item.code, item.name),
        "item_code": str(item.code or ""),
        "item_name": str(item.name or ""),
        "source_kind": "excel-target",
        "source_label": source_label,
        "target_key": candidates[0].target_key,
        "source_file": source_files,
        "identity_evidence_kind": identity_evidence_kind,
        "identity_evidence": identity_evidence,
        "compatibility_status": "rejected",
        "candidate_compatibility_status": _candidate_compatibility_status(candidates),
        "compatibility_rejection": compatibility_rejection,
        "candidate_count_total": candidate_count_total,
        "candidate_count_saved": len(candidates),
        "options": [
            candidate.to_review_candidate_dict() for candidate in candidates
        ],
    }
    with candidates_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _candidate_compatibility_status(candidates) -> str:
    statuses = {candidate.compatibility_status for candidate in candidates}
    if "compatible" in statuses:
        return "compatible"
    if "rejected" in statuses:
        return "rejected"
    return "unknown"


def _auto_save_excel_target_match(
    app_config: AppConfig,
    item: Item,
    best: dict,
    *,
    target_key: str,
    source_file: str,
    run_id: str,
) -> None:
    """Save a verified Excel-target match with explicit provenance."""
    matching = getattr(app_config, "matching", None)
    if not matching or not getattr(matching, "enable_auto_save_verified_match", False):
        return
    try:
        store = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB)
        source_label = _excel_target_source_label(target_key, source_file)
        existing = store.lookup(
            item.code,
            item.name,
            matching_source="excel-target",
            excel_target_key=target_key,
        )
        if existing is None:
            # Decisions created before source provenance existed remain a
            # conservative safeguard, but a decision from another known
            # supplier must never block this Excel target.
            existing = store.lookup(
                item.code, item.name, matching_source="legacy-unknown"
            )
        if existing and existing.manual_decision in {"approved_match", "not_matching"}:
            return
        store_id = candidate_store_product_id(best)
        decision = ManualReviewDecision(
            item_code=item.code,
            item_name=item.name,
            approved=True,
            correct_store_product_id=store_id,
            correct_product_name=str(
                best.get("productNameEn") or best.get("productNameEnFallback") or ""
            ),
            correct_product_name_ar=str(best.get("productName") or ""),
            run_id=run_id,
            manual_decision="auto_matched",
            excel_target_key=target_key,
            excel_target_source_file=source_file,
            matching_source="excel-target",
            matching_source_label=source_label,
            identity_evidence_kind=str(best.get("identity_evidence_kind") or ""),
            identity_evidence=str(best.get("identity_evidence") or ""),
        )
        store.upsert(decision)
    except Exception:
        logger.warning(
            "could not auto-save Excel-target match",
            extra={"item_code": str(item.code), "target_key": target_key},
            exc_info=True,
        )


__all__ = [
    "selected_excel_target_configs",
    "load_target_catalogs",
    "run_excel_target_match_only",
    "run_excel_target_match_only_multi",
]


def _extract_run_id(run_key: str | None) -> str | None:
    """Return the run-id half of a ``profile/run-id`` key, or None."""
    if not run_key or "/" not in run_key:
        return None
    return run_key.split("/", 1)[1] or None


def _ensure_run_record(
    app_config: AppConfig, run_key: str | None, run, target_key: str
) -> None:
    """Open the order-runs record for an excel-target match-only run.

    The excel-target flow does not call the Tawreed ``open_run_record``
    helper because there is no Tawreed profile driving the run. We still
    need a parent ``runs`` row so the ``run_items`` foreign key resolves
    and the Run DB tab can show the run in its header.
    """
    if not run_key or "/" not in run_key:
        return
    from src.core.database.order_runs_store import OrderRunsStore
    from src.core.ordering.order_run_persistence import open_run_record

    profile_key, _run_id = run_key.split("/", 1)
    database = getattr(app_config, "database", None)
    options = database.persistence_options() if database else {}
    try:
        store = OrderRunsStore(options.get("path"))
    except Exception:
        logger.debug(
            "could not open OrderRunsStore for excel-target run",
            extra={"run_key": run_key},
            exc_info=True,
        )
        return
    if store.run_exists(run_key):
        return
    run_options = {
        "mode": "match-only",
        "execution_mode": "excel-target",
        "warehouse_mode": "",
        "min_discount_pct": None,
        "matching_risk": "",
        "excel_source": target_key,
        "item_workers": 1,
        "artifact_dir": str(run.directory),
    }
    opened = open_run_record(profile_key, run.run_id, run_options, options)
    if opened is None:
        logger.debug(
            "excel-target run record could not be opened",
            extra={"run_key": run_key, "target": target_key},
        )


def _finish_run_record(app_config: AppConfig, run_key: str | None) -> None:
    """Mark the excel-target run as finished, swallowing persistence errors."""
    if not run_key:
        return
    from src.core.ordering.order_run_persistence import finish_run_record

    database = getattr(app_config, "database", None)
    options = database.persistence_options() if database else {}
    finish_run_record(run_key, options)


def _build_db_persister(
    app_config: AppConfig, run_key: str | None, target_key: str
):
    """Return a callback that mirrors one match result into order_runs.db.

    When ``run_key`` is None the callback is a no-op so the legacy callers
    that only want the CSV artifact keep working without a database round
    trip.
    """
    if not run_key:
        return lambda *args, **kwargs: None

    from src.core.ordering.order_run_persistence import record_run_item

    database = getattr(app_config, "database", None)
    options = database.persistence_options() if database else {}

    def _persist(
        item,
        *,
        status,
        score,
        reason,
        source_file,
        best: dict | None = None,
        matched_name: str = "",
        matched_price: str = "",
        matched_discount: str = "",
        candidate_count: int = 0,
        candidate_count_total: int = 0,
        manual_review_required: bool = False,
        manual_review_category: str = "",
    ) -> None:
        summary_row = {
            "item_code": str(item.code or ""),
            "item_name": str(item.name or ""),
            "item_qty": int(getattr(item, "qty", 0) or 0),
            "status": str(status),
            "reason": str(reason or ""),
            "matched": 1 if status == "matched-only" and not manual_review_required else 0,
            "manual_review_required": bool(manual_review_required),
            "manual_review_category": str(manual_review_category or ""),
            "candidate_count": int(candidate_count or 0),
            "candidate_count_total": int(candidate_count_total or 0),
            "matched_query": "",
            "deterministic_score": float(score or 0.0),
            "winner_store_key": "",
            "winner_store_product_id": "",
            "tie_break_reason": "",
            "ordered_total_qty": 0,
            "elapsed_seconds": 0.0,
            "match_elapsed_seconds": 0.0,
            "matched_name": matched_name,
            "matched_name_ar": matched_name,
            "matched_name_en": matched_name,
            "matched_product_name_ar": matched_name,
            "matched_product_name_en": matched_name,
            "matched_price": matched_price,
            "matched_discount": matched_discount,
        }
        label = str(target_key or "")
        if source_file:
            label = f"{label}@{source_file}"
        snapshot_kwargs: dict = {
            "source_kind": "excel-target",
            "source_label": label,
            "store_source": "excel_target",
            "store_source_owner": str(target_key or ""),
            "stores": [],
            "store_selections": [],
        }
        snapshot_kwargs["candidates_considered"] = int(candidate_count_total or candidate_count or 0)
        if best is not None:
            store_dict = _excel_target_store_dict(
                target_key, source_file, best
            )
            snapshot_kwargs.update(
                {
                    "stores": [store_dict],
                    "store_selections": [(store_dict, 0)],
                }
            )
        record_run_item(run_key, summary_row, options=options, **snapshot_kwargs)

    return _persist


def _excel_target_store_dict(
    target_key: str, source_file: str, best: dict
) -> dict:
    """Return a store-row dict for ``run_item_stores`` from one Excel match.

    The shape matches what the Tawreed store-snapshot writer consumes
    (:func:`usable_store_rows`, :func:`store_price_fields`,
    :func:`candidate_store_product_id`, :func:`store_identity_key`).

    Excel catalogs declare their price column under ``priceMeaning``:

    - ``public_with_discount`` (default): the column carries the
      retail price. We forward it as ``price`` (which
      :data:`PUBLIC_PRICE_KEYS` reads) and let the resolver derive
      ``purchase_price = public × (1 − discount)``.
    - ``purchase_only``: the column carries the pharmacy's purchase
      price. We forward it as ``salePrice`` (which
      :data:`PURCHASE_PRICE_KEYS` reads).
    - ``public_only``: the column carries the retail price only; the
      purchase side stays ``NULL``.

    The warehouse identity is derived from the target key + source file
    so the row groups under one entry per catalog.
    """
    name = (
        best.get("productNameEn")
        or best.get("productName")
        or best.get("name")
        or ""
    )
    discount = best.get("discountPercent", best.get("discount", 0)) or 0
    price = best.get("salePrice")
    if price is None:
        price = best.get("price")
    price_meaning = best.get("priceMeaning") or "public_with_discount"
    label = f"excel-target:{target_key}"
    if source_file:
        label = f"{label}@{source_file}"
    row: dict = {
        "storeProductId": str(best.get("storeProductId") or best.get("id") or name),
        "storeName": label,
        "storeNameEn": label,
        "companyName": label,
        "productNameEn": str(name),
        "productName": str(name),
        "discountPercent": float(discount),
        "availableQuantity": 1,
        "productsCount": 1,
        "currency": "",
        "priceMeaning": price_meaning,
        "excelTarget": True,
    }
    # Keep an absent/blank catalog price absent.  A real numeric zero remains
    # valid and must be retained as zero for the resolver and cart gate.
    if price is not None:
        if price_meaning == "purchase_only":
            row["salePrice"] = float(price)
        else:
            row["price"] = float(price)
    return row
