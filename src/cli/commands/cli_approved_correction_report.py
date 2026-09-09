"""Read-only export of approved Excel-target correction evidence.

The command is deliberately a thin driving adapter.  It resolves workbook
paths, takes a read-only snapshot of Saved Corrections, delegates the
counterfactual work to the core analyzer, and writes two immutable artifacts.
It never calls ``ManualReviewStore.upsert`` (or any other write API).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.core.config.config_models import AppConfig
from src.core.errors import ArtifactError, ValidationError
from src.core.excel_target.excel_target_loader import (
    TargetProduct,
    load_target_catalog_from_excel,
)
from src.core.excel_target.excel_target_matching import ExcelTargetMatcher
from src.core.manual_review.manual_review_store import ManualReviewDecision
from src.core.manual_review.manual_review_store_helpers import _decision_from_row
from src.core.manual_review.manual_review_store_sql import SELECT_DECISIONS
from src.core.manual_review.manual_review_store import DEFAULT_MANUAL_REVIEW_DB

from ..registry import register

logger = logging.getLogger(__name__)

REPORT_SCHEMA_VERSION = 1
REPORT_JSON_FILENAME = "approved_correction_report.json"
REPORT_CSV_FILENAME = "approved_correction_findings.csv"

_FINDING_COLUMNS = (
    "item_code",
    "item_name",
    "target_key",
    "row_key",
    "excel_target_source_file",
    "excel_target_source_row",
    "approval_run_id",
    "catalog_fingerprint",
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
)


# Imported lazily by default so the CLI adapter remains importable while the
# core task is being developed in parallel.  Tests can patch this seam with a
# contract-compatible analyzer without touching the matcher implementation.
try:  # pragma: no cover - exercised when the core analyzer is available
    from src.core.excel_target.approved_correction_analysis import (
        analyze_approved_corrections,
    )
except ModuleNotFoundError:  # pragma: no cover - temporary parallel-work seam
    analyze_approved_corrections = None


@register("approved-correction-report")
def run_approved_correction_report_command(
    app_config: AppConfig, args: argparse.Namespace
) -> int:
    """Generate approved-correction JSON/CSV artifacts without state writes."""
    selected = _resolve_report_targets(app_config, args)
    catalogs: dict[str, list[TargetProduct]] = {}
    for target_key, paths in selected:
        target_config = app_config.excel_targets[target_key]
        merged: list[TargetProduct] = []
        for workbook_path in paths:
            merged.extend(
                load_target_catalog_from_excel(
                    workbook_path,
                    target_config,
                    source_file=workbook_path.name,
                )
            )
        catalogs[target_key] = merged

    decisions = _read_decisions_read_only(
        Path(getattr(args, "manual_review_db", "") or DEFAULT_MANUAL_REVIEW_DB)
    )
    analyzer = analyze_approved_corrections
    if analyzer is None:
        raise ArtifactError(
            "The approved-correction analyzer is unavailable.",
            hint="Implement src.core.excel_target.approved_correction_analysis first.",
        )

    report = analyzer(
        decisions=decisions,
        catalogs=catalogs,
        matching_config=app_config.matching,
        matcher_factory=_matcher_factory,
    )
    output_dir = Path(getattr(args, "output", "") or "")
    if not str(output_dir):
        raise ValidationError("--output is required for approved-correction-report.")
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = _report_payload(report, catalogs)
    _write_json(output_dir / REPORT_JSON_FILENAME, payload)
    _write_csv(output_dir / REPORT_CSV_FILENAME, payload["findings"])
    logger.info(
        "approved correction report written",
        extra={"output_dir": str(output_dir), "finding_count": len(payload["findings"])},
    )
    return 0


def _resolve_report_targets(
    app_config: AppConfig, args: argparse.Namespace
) -> list[tuple[str, list[Path]]]:
    """Resolve and validate one explicit workbook path per target key."""
    raw_targets = getattr(args, "excel_target", None) or []
    if isinstance(raw_targets, str):
        raw_targets = [raw_targets]
    target_keys = [str(value).strip() for value in raw_targets if str(value).strip()]
    if not target_keys:
        raise ValidationError(
            "At least one --excel-target is required.",
            hint="Repeat --excel-target KEY for each catalog to audit.",
        )
    duplicates = _duplicates(target_keys)
    if duplicates:
        raise ValidationError(
            f"Duplicate Excel target key: {duplicates[0]}",
            hint="Specify each target key once.",
        )

    configured = app_config.excel_targets
    unknown = [key for key in target_keys if key not in configured]
    if unknown:
        raise ValidationError(f"Unknown Excel target key: {unknown[0]}")

    raw_paths = getattr(args, "excel_target_path", None) or []
    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]
    path_by_key: dict[str, Path] = {}
    for raw in raw_paths:
        text = str(raw).strip()
        if "=" not in text:
            raise ValidationError(
                f"Invalid --excel-target-path value: {text!r}",
                hint="Use KEY=PATH.",
            )
        key, path_text = text.split("=", 1)
        key = key.strip()
        path_text = path_text.strip()
        if not key or not path_text:
            raise ValidationError(
                f"Invalid --excel-target-path value: {text!r}",
                hint="Use KEY=PATH with both parts present.",
            )
        if key in path_by_key:
            raise ValidationError(f"Duplicate Excel target path key: {key}")
        if key not in configured:
            raise ValidationError(f"Unknown Excel target key in path override: {key}")
        path_by_key[key] = Path(path_text)

    missing_paths = [key for key in target_keys if key not in path_by_key]
    if missing_paths:
        raise ValidationError(
            f"Missing workbook path for Excel target: {missing_paths[0]}",
            hint="Provide --excel-target-path KEY=PATH for every selected target.",
        )
    missing_files = [key for key in target_keys if not path_by_key[key].is_file()]
    if missing_files:
        path = path_by_key[missing_files[0]]
        raise ValidationError(f"Excel target workbook not found: {path}")
    return [(key, [path_by_key[key]]) for key in target_keys]


def _duplicates(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    duplicate: list[str] = []
    for value in values:
        if value in seen and value not in duplicate:
            duplicate.append(value)
        seen.add(value)
    return duplicate


def _matcher_factory(
    target_key: str,
    catalog: Sequence[TargetProduct],
    **kwargs: Any,
) -> ExcelTargetMatcher:
    """Construct a matcher with saved approvals explicitly disabled."""
    kwargs.pop("use_saved_approvals", None)
    return ExcelTargetMatcher(
        target_key,
        catalog,
        allow_live_translation=False,
        use_saved_approvals=False,
        **kwargs,
    )


def _read_decisions_read_only(path: Path) -> list[ManualReviewDecision]:
    """Read Saved Corrections through SQLite's read-only URI mode."""
    path = path.expanduser()
    if not path.is_file():
        raise ValidationError(f"Saved Corrections database not found: {path}")
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = None
    try:
        connection = sqlite3.connect(uri, uri=True)
        with connection:
            columns = {
                str(row[1])
                for row in connection.execute(
                    "pragma table_info(manual_review_decisions)"
                ).fetchall()
            }
            ordering = "updated_at desc" if "updated_at" in columns else "rowid desc"
            rows = connection.execute(
                SELECT_DECISIONS + f" order by {ordering}"
            ).fetchall()
    except sqlite3.Error as exc:
        raise ArtifactError(
            f"Could not read Saved Corrections database: {path}",
            hint="Use a valid, initialized manual_review_decisions.db.",
        ) from exc
    finally:
        if connection is not None:
            connection.close()
    return [_decision_from_row(row) for row in rows]


def _matcher_catalog_fingerprint(
    target_key: str, catalog: Sequence[TargetProduct]
) -> str:
    """Hash canonical target provenance so workbook drift is visible."""
    try:
        from src.core.excel_target.approved_correction_analysis import catalog_fingerprint

        return catalog_fingerprint(target_key, catalog)
    except (ImportError, TypeError):
        # Keep the adapter importable during the parallel core implementation.
        # The production analyzer's fingerprint is preferred whenever present.
        pass
    rows = [
        (
            product.source_file,
            int(product.source_row_number or 0),
            product.store_product_id,
            product.name_ar,
            product.trusted_name_en,
        )
        for product in catalog
    ]
    material = json.dumps(sorted(rows), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _report_payload(report: Any, catalogs: Mapping[str, Sequence[TargetProduct]]) -> dict[str, Any]:
    findings = [_to_mapping(finding) for finding in getattr(report, "findings", ())]
    recommendations = [
        _to_mapping(recommendation)
        for recommendation in getattr(report, "recommendations", ())
    ]
    counts_by_root_cause = dict(getattr(report, "counts_by_root_cause", {}) or {})
    counts_by_match_origin = dict(
        getattr(report, "counts_by_match_origin", {}) or {}
    )
    counts = dict(getattr(report, "counts", {}) or {})
    counts.update(
        {
            str(key): int(value)
            for key, value in dict(
                getattr(report, "counts_by_match_origin", {}) or {}
            ).items()
        }
    )
    for finding in findings:
        root_cause = str(finding.get("root_cause") or "")
        if root_cause:
            counts_by_root_cause.setdefault(root_cause, 0)
    derived_counts: dict[str, int] = {}
    for finding in findings:
        origin = str(finding.get("match_origin") or "")
        if origin in {
            "automatic_verified",
            "approved_manual_override",
            "saved_auto_matched",
            "approval_outside_current_input",
        }:
            derived_counts[origin] = derived_counts.get(origin, 0) + 1
        status = str(finding.get("approval_status") or "")
        if status in {"stale", "invalid"}:
            derived_counts["stale_or_invalid"] = derived_counts.get("stale_or_invalid", 0) + 1
    for key in (
        "automatic_verified",
        "approved_manual_override",
        "saved_auto_matched",
        "stale_or_invalid",
        "approval_outside_current_input",
    ):
        counts[key] = max(counts.get(key, 0), derived_counts.get(key, 0))
    for key, value in derived_counts.items():
        counts[key] = max(counts.get(key, 0), value)
    counts["approval_outside_current_input"] = max(
        counts["approval_outside_current_input"],
        counts_by_match_origin.get("approval_outside_current_input", 0),
    )
    fingerprints = dict(getattr(report, "catalog_fingerprints", {}) or {})
    fingerprints.update(
        {
            key: _matcher_catalog_fingerprint(key, catalog)
            for key, catalog in catalogs.items()
            if key not in fingerprints
        }
    )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_schema_version": f"approved-correction-report/v{REPORT_SCHEMA_VERSION}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_catalog_fingerprints": fingerprints,
        "counts": counts,
        "counts_by_root_cause": counts_by_root_cause,
        "counts_by_match_origin": counts_by_match_origin,
        "findings": findings,
        "recommendations": recommendations,
    }


def _to_mapping(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    raise TypeError(f"Analyzer returned unsupported report value: {type(value)!r}")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError as exc:
        raise ArtifactError(f"Could not write JSON report: {path}") from exc


def _write_csv(path: Path, findings: Sequence[Mapping[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(_FINDING_COLUMNS), extrasaction="ignore")
            writer.writeheader()
            for finding in findings:
                writer.writerow(
                    {
                        key: _csv_value(finding.get(key, ""))
                        for key in _FINDING_COLUMNS
                    }
                )
        temporary.replace(path)
    except OSError as exc:
        raise ArtifactError(f"Could not write CSV report: {path}") from exc


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


__all__ = [
    "REPORT_SCHEMA_VERSION",
    "run_approved_correction_report_command",
]
