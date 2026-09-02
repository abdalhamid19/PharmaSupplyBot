"""Excel target order item flow — match-only against in-memory catalogs."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterable

from src.core.artifact_run import artifact_run
from src.core.config.config_models import AppConfig
from src.core.excel_target import (
    TargetProduct,
    find_best_match_in_target,
    load_target_catalog_from_excel,
    match_item_against_all_targets,
    first_accepted_match,
)
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
    matched = flagged = 0
    items_list = list(items)
    db_persist = _build_db_persister(run_key, target_key)
    provided_run_id = _extract_run_id(run_key) if run_key else None
    with artifact_run("excel-target", target_key, run_id=provided_run_id) as run:
        _ensure_run_record(app_config, run_key, run, target_key)
        target_summary = (
            run.directory / f"{MATCH_ONLY_SUMMARY_LABEL}_{target_key}.csv"
        )
        with target_summary.open("w", newline="", encoding="utf-8") as fh:
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
                ]
            )
            for item in items_list:
                result = find_best_match_in_target(
                    item, target_key, catalog, app_config.matching
                )
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
                        ]
                    )
                    db_persist(
                        item,
                        status="no-results",
                        score=0.0,
                        reason="no catalog",
                        source_file="",
                    )
                    continue
                decision = result.decision
                best = decision.best_match
                if best is None:
                    score = (
                        f"{decision.diagnostics[0].score:.2f}"
                        if decision.diagnostics
                        else "0"
                    )
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
                        ]
                    )
                    flagged += 1
                    db_persist(
                        item,
                        status="no-results",
                        score=float(score or 0),
                        reason=decision.final_reason,
                        source_file="",
                        best=None,
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
                        str(best.data.get("productNameEn", "")),
                        str(best.data.get("salePrice", "")),
                        str(best.data.get("discountPercent", "")),
                        "matched-only",
                        f"{best.score:.2f}",
                        decision.final_reason,
                    ]
                )
                matched += 1
                db_persist(
                    item,
                    status="matched-only",
                    score=best.score,
                    reason=decision.final_reason,
                    source_file=source_file,
                    best=best.data,
                    matched_name=str(best.data.get("productNameEn", "")),
                    matched_price=str(best.data.get("salePrice", "")),
                    matched_discount=str(best.data.get("discountPercent", "")),
                )
        try:
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            target_summary.replace(summary_path)
        except OSError:
            logger.debug(
                "could not mirror excel-target summary", extra={"path": str(summary_path)}
            )

    _finish_run_record(app_config, run_key)
    return {
        "processed": len(items_list),
        "matched": matched,
        "flagged": flagged,
    }


def run_excel_target_match_only_multi(
    app_config: AppConfig,
    selected: list[tuple[str, list[Path]]],
    catalogs: dict[str, list[TargetProduct]],
    items: Iterable[Item],
    summary_path: Path,
    run_key: str | None = None,
) -> dict[str, dict[str, int]]:
    """Run match-only across every Excel target, returning per-target totals."""
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
        )
    return totals


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


def _build_db_persister(run_key: str | None, target_key: str):
    """Return a callback that mirrors one match result into order_runs.db.

    When ``run_key`` is None the callback is a no-op so the legacy callers
    that only want the CSV artifact keep working without a database round
    trip.
    """
    if not run_key:
        return lambda *args, **kwargs: None

    from src.core.ordering.order_run_persistence import record_run_item

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
    ) -> None:
        summary_row = {
            "item_code": str(item.code or ""),
            "item_name": str(item.name or ""),
            "item_qty": int(getattr(item, "qty", 0) or 0),
            "status": str(status),
            "reason": str(reason or ""),
            "matched": 1 if status == "matched-only" else 0,
            "manual_review_required": 0,
            "manual_review_category": "",
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
        snapshot_kwargs: dict = {"source_kind": "excel-target", "source_label": label}
        if best is not None:
            store_dict = _excel_target_store_dict(
                target_key, source_file, best
            )
            snapshot_kwargs.update(
                {
                    "stores": [store_dict],
                    "store_selections": [(store_dict, 0)],
                    "store_source": "excel_target",
                }
            )
        record_run_item(run_key, summary_row, **snapshot_kwargs)

    return _persist


def _excel_target_store_dict(
    target_key: str, source_file: str, best: dict
) -> dict:
    """Return a store-row dict for ``run_item_stores`` from one Excel match.

    The shape matches what the Tawreed store-snapshot writer consumes
    (:func:`usable_store_rows`, :func:`store_price_fields`,
    :func:`candidate_store_product_id`, :func:`store_identity_key`). Excel
    catalogs only carry the pharmacy's purchase price + discount + name, so
    the public/retail price is left empty and the warehouse identity is
    derived from the target key + source file so the row groups under one
    entry per catalog.
    """
    name = (
        best.get("productNameEn")
        or best.get("productName")
        or best.get("name")
        or ""
    )
    discount = best.get("discountPercent", best.get("discount", 0)) or 0
    price = best.get("salePrice", best.get("price", 0)) or 0
    label = f"excel-target:{target_key}"
    if source_file:
        label = f"{label}@{source_file}"
    return {
        "storeProductId": str(best.get("storeProductId") or best.get("id") or name),
        "storeName": label,
        "storeNameEn": label,
        "companyName": label,
        "productNameEn": str(name),
        "productName": str(name),
        "salePrice": float(price),
        "sellingPrice": float(price),
        "discountPercent": float(discount),
        "availableQuantity": 1,
        "productsCount": 1,
        "currency": "",
    }
