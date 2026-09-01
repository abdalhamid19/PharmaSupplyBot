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


def selected_excel_target_configs(app_config: AppConfig, args) -> list[tuple[str, Path]]:
    """Resolve the list of Excel targets the run should match against.

    Resolution priority:
    1. ``--excel-target <key>`` (single target by config key)
    2. ``--all-excel-targets`` (every enabled target)
    3. ``--excel-target-path <path>`` (override one target's XLSX path)

    Each resolved entry is ``(target_key, catalog_xlsx_path)``.
    """
    enabled = app_config.enabled_excel_targets()
    if not enabled:
        return []

    target_path_overrides: dict[str, str] = {}
    raw_override = getattr(args, "excel_target_path", None)
    if raw_override:
        for entry in raw_override.split(","):
            entry = entry.strip()
            if not entry or "=" not in entry:
                continue
            key, _, path = entry.partition("=")
            target_path_overrides[key.strip()] = path.strip()

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
    resolved: list[tuple[str, Path]] = []
    for target_key, target_cfg in targets:
        if target_key in target_path_overrides:
            xlsx_path = Path(target_path_overrides[target_key])
        else:
            xlsx_path = default_dir / f"{target_key}.xlsx"
        resolved.append((target_key, xlsx_path))
    return resolved


def load_target_catalogs(
    selected: list[tuple[str, Path]], app_config: AppConfig
) -> dict[str, list[TargetProduct]]:
    """Read every resolved Excel target catalog into memory."""
    catalogs: dict[str, list[TargetProduct]] = {}
    for target_key, xlsx_path in selected:
        if target_key not in app_config.excel_targets:
            continue
        target_cfg = app_config.excel_targets[target_key]
        try:
            catalogs[target_key] = load_target_catalog_from_excel(xlsx_path, target_cfg)
        except FileNotFoundError as error:
            logger.warning(
                "excel target catalog missing",
                extra={"target": target_key, "path": str(xlsx_path)},
            )
            logger.debug("excel target load failure: %s", error)
            catalogs[target_key] = []
    return catalogs


def run_excel_target_match_only(
    app_config: AppConfig,
    target_key: str,
    items: Iterable[Item],
    catalog: list[TargetProduct],
    summary_path: Path,
) -> dict[str, int]:
    """Run match-only for one Excel target and persist a summary CSV.

    Returns counters ``{"processed": N, "matched": M, "flagged": F}`` for the
    target. Each row mirrors the Tawreed match-only summary shape so the
    downstream tools (``render_fresh_run_analysis``, ``Run DB``) work without
    changes.
    """
    matched = flagged = 0
    items_list = list(items)
    with artifact_run("excel-target", target_key) as run:
        target_summary = (
            run.directory / f"{MATCH_ONLY_SUMMARY_LABEL}_{target_key}.csv"
        )
        with target_summary.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "target_kind",
                    "target_key",
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
                    continue
                decision = result.decision
                best = decision.best_match
                if best is None:
                    writer.writerow(
                        [
                            "excel-target",
                            target_key,
                            item.code,
                            item.name,
                            "",
                            "",
                            "",
                            "no-results",
                            f"{decision.diagnostics[0].score:.2f}" if decision.diagnostics else "0",
                            decision.final_reason,
                        ]
                    )
                    flagged += 1
                    continue
                writer.writerow(
                    [
                        "excel-target",
                        target_key,
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
        # Mirror the summary at the requested path so the operator can find it.
        try:
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            target_summary.replace(summary_path)
        except OSError:
            logger.debug(
                "could not mirror excel-target summary", extra={"path": str(summary_path)}
            )

    return {
        "processed": len(items_list),
        "matched": matched,
        "flagged": flagged,
    }


def run_excel_target_match_only_multi(
    app_config: AppConfig,
    selected: list[tuple[str, Path]],
    catalogs: dict[str, list[TargetProduct]],
    items: Iterable[Item],
    summary_path: Path,
) -> dict[str, dict[str, int]]:
    """Run match-only across every Excel target, returning per-target totals."""
    items_list = list(items)
    totals: dict[str, dict[str, int]] = {}
    for target_key, _xlsx_path in selected:
        catalog = catalogs.get(target_key, [])
        totals[target_key] = run_excel_target_match_only(
            app_config,
            target_key,
            items_list,
            catalog,
            summary_path=summary_path.with_name(
                f"{summary_path.stem}_{target_key}{summary_path.suffix}"
            ),
        )
    return totals


__all__ = [
    "selected_excel_target_configs",
    "load_target_catalogs",
    "run_excel_target_match_only",
    "run_excel_target_match_only_multi",
]