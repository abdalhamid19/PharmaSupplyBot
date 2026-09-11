"""Read-only measurement of the saved and displayed manual-review candidates.

The display measurement deliberately calls the real Streamlit page entry point
and replaces only the side effects: the decision store, Streamlit widgets, and
the card renderer.  It therefore measures the boundary immediately before
candidate widgets are built without writing to SQLite, workbooks, or artifacts.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from unittest.mock import patch


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui.manual_review import streamlit_manual_review_page as page


ITEMS_PER_PAGE = 50


@dataclass(frozen=True)
class SavedCounts:
    """Strict result of reading explicit ``candidate_count_saved`` values."""

    status: str
    count: int | None
    errors: tuple[str, ...]


@dataclass(frozen=True)
class DisplaySettings:
    """Immutable settings used for one display measurement."""

    display_limit: int
    hide_completed: bool
    decisions: dict[tuple[str, str], list[Any]] | None


@dataclass(frozen=True)
class ReportData:
    """Inputs collected before serializing one measurement report."""

    run_dirs: tuple[Path, ...]
    saved: SavedCounts
    display: dict[str, Any]
    settings: dict[str, Any]
    status: str
    errors: list[str]


class ReadOnlyStore:
    """Decision-store double that makes accidental writes fail loudly."""

    def __init__(self, decisions: dict[tuple[str, str], list[Any]] | None = None):
        self._decisions = decisions or {}

    def lookup_all(self, item_code: str, item_name: str) -> list[Any]:
        return list(self._decisions.get((item_code, item_name), ()))

    def __getattr__(self, name: str):
        if name in {"upsert", "upsert_batch", "execute_update", "commit", "close"}:
            raise AssertionError(f"read-only measurement attempted store write: {name}")
        raise AttributeError(name)


def read_explicit_saved_counts(run_dirs: Iterable[Path]) -> SavedCounts:
    """Read ``C_saved`` strictly from JSONL envelope fields.

    Legacy records without the explicit field are intentionally reported as
    ``not_measured`` instead of silently using ``len(options)``.
    """
    count = 0
    errors: list[str] = []
    seen_files: set[Path] = set()
    for file_path in _candidate_files(run_dirs):
        if file_path in seen_files:
            continue
        seen_files.add(file_path)
        file_count, file_errors = _read_saved_file(file_path)
        count += file_count
        errors.extend(file_errors)
    if errors:
        status = "not_measured" if any("missing" in error for error in errors) else "inconsistent"
        return SavedCounts(status, None, tuple(errors))
    return SavedCounts("measured", count, ())


def _candidate_files(run_dirs: Iterable[Path]) -> list[Path]:
    files = {
        file_path.resolve()
        for run_dir in run_dirs
        for file_path in run_dir.glob("manual_review_candidates_*.jsonl")
    }
    return sorted(files)


def _read_saved_file(file_path: Path) -> tuple[int, list[str]]:
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return 0, [f"{file_path}: unreadable: {exc}"]
    count = 0
    errors: list[str] = []
    item_keys: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        saved, record_errors = _parse_saved_record(file_path, line_number, line, item_keys)
        count += saved
        errors.extend(record_errors)
    return count, errors


def _parse_saved_record(
    file_path: Path, line_number: int, line: str, item_keys: set[str]
) -> tuple[int, list[str]]:
    if not line.strip():
        return 0, []
    try:
        record = json.loads(line)
    except json.JSONDecodeError as exc:
        return 0, [f"{file_path}:{line_number}: invalid JSON: {exc}"]
    if not isinstance(record, dict):
        return 0, [f"{file_path}:{line_number}: record is not an object"]
    errors = _record_identity_errors(file_path, line_number, record, item_keys)
    saved = record.get("candidate_count_saved")
    errors.extend(_saved_count_errors(file_path, line_number, saved, record.get("options")))
    return (saved if not errors else 0), errors


def _saved_count_errors(file_path, line_number, saved, options) -> list[str]:
    if type(saved) is not int or saved < 0:
        return [f"{file_path}:{line_number}: missing or invalid candidate_count_saved"]
    if not isinstance(options, list):
        return [f"{file_path}:{line_number}: options is not a list"]
    if saved != len(options):
        return [
            f"{file_path}:{line_number}: candidate_count_saved={saved} "
            f"does not equal options={len(options)}"
        ]
    return []


def _record_identity_errors(
    file_path: Path, line_number: int, record: dict[str, Any], item_keys: set[str]
) -> list[str]:
    item_key = str(record.get("item_key") or "").strip()
    item_key = item_key or f"{record.get('item_code', '')}::{record.get('item_name', '')}"
    errors: list[str] = []
    if item_key in item_keys:
        errors.append(f"{file_path}:{line_number}: duplicate item_key {item_key}")
    item_keys.add(item_key)
    return errors


def measure_display(
    run_dirs: Iterable[Path],
    *,
    display_limit: int = 5,
    hide_completed: bool = False,
    decisions: dict[tuple[str, str], list[Any]] | None = None,
) -> dict[str, Any]:
    """Measure the actual ``render_run_candidates`` card boundary read-only."""
    normalized_dirs = tuple(Path(run_dir) for run_dir in run_dirs)
    if not normalized_dirs:
        raise ValueError("at least one run directory is required")
    loaded = page._load_group_candidates(normalized_dirs)
    pages = max(1, math.ceil(len(loaded) / ITEMS_PER_PAGE))
    settings = DisplaySettings(display_limit, hide_completed, decisions)
    captured = _capture_pages(normalized_dirs, pages, settings)
    return _display_metrics(loaded, captured, pages)


def _capture_pages(run_dirs, page_count, settings: DisplaySettings):
    captured: list[dict[str, Any]] = []
    session_state: dict[str, Any] = {}
    store = ReadOnlyStore(settings.decisions)
    with ExitStack() as stack:
        for context in _streamlit_measurement_patches(settings, store, session_state, captured):
            stack.enter_context(context)
        for current_page in range(1, page_count + 1):
            session_state["manual_review_page"] = current_page
            page.render_run_candidates(run_dirs)
    return captured


def _streamlit_measurement_patches(settings, store, session_state, captured):
    card_capture = CardCapture(captured)
    return (
        patch.object(page, "manual_review_store_or_stop", return_value=store),
        patch.object(page, "_candidate_display_limit", return_value=settings.display_limit),
        patch.object(page, "_render_item_card", side_effect=card_capture),
        patch.object(page.st, "subheader"),
        patch.object(page.st, "caption"),
        patch.object(page.st, "success"),
        patch.object(page.st, "checkbox", return_value=settings.hide_completed),
        patch.object(page.st, "session_state", session_state),
    )


class CardCapture:
    """Capture options at the exact card-rendering boundary."""

    def __init__(self, captured: list[dict[str, Any]]):
        self.captured = captured

    def __call__(self, *callback_args):
        item_key, _item, visible_options, run_dir, _store = callback_args
        self.captured.append(
            {
                "item_key": item_key,
                "run_dir": str(run_dir),
                "row_keys": [option.excel_target_row_key for option in visible_options],
                "candidate_methods": [option.candidate_method for option in visible_options],
                "ranking_tiers": [option.ranking_tier for option in visible_options],
                "count": len(visible_options),
            }
        )


def _display_metrics(loaded, captured, pages):
    loaded_count = sum(len(options) for options in loaded.values())
    display_count = sum(record["count"] for record in captured)
    errors = _display_invariant_errors(captured, display_count, loaded_count)
    return {
        "c_loaded_unique": loaded_count,
        "c_display_run": display_count,
        "c_display_pages": [_page_count(captured, page_number) for page_number in range(1, pages + 1)],
        "displayed_items": len(captured),
        "captured": captured,
        "row_keys": [row_key for record in captured for row_key in record["row_keys"]],
        "invariants": {"passed": not errors, "errors": errors},
    }


def _display_invariant_errors(captured, display_count, loaded_count):
    item_keys = [record["item_key"] for record in captured]
    duplicates = sorted(item_key for item_key in set(item_keys) if item_keys.count(item_key) > 1)
    errors = []
    if duplicates:
        errors.append(f"duplicate displayed item keys: {duplicates}")
    if display_count > loaded_count:
        errors.append("C_display_run exceeds C_loaded_unique")
    return errors


def _page_count(captured: list[dict[str, Any]], page_number: int) -> int:
    start = (page_number - 1) * ITEMS_PER_PAGE
    return sum(record["count"] for record in captured[start : start + ITEMS_PER_PAGE])


def build_report(run_dirs: Iterable[Path], **settings: Any) -> dict[str, Any]:
    """Build the documented JSON report for one merged Streamlit run."""
    normalized_dirs = tuple(Path(run_dir) for run_dir in run_dirs)
    saved = read_explicit_saved_counts(normalized_dirs)
    display = measure_display(normalized_dirs, **settings)
    status, errors = _report_status(saved, display)
    report_data = ReportData(normalized_dirs, saved, display, settings, status, errors)
    return _report_payload(report_data)


def _report_status(saved: SavedCounts, display: dict[str, Any]) -> tuple[str, list[str]]:
    status = saved.status
    errors = list(saved.errors) + list(display["invariants"]["errors"])
    if not display["invariants"]["passed"]:
        status = "inconsistent"
    if saved.count is not None and display["c_loaded_unique"] > saved.count:
        status = "inconsistent"
        errors.append("C_loaded_unique exceeds C_saved_artifact")
    return status, errors


def _report_payload(report: ReportData):
    return {
        "schema_version": 1,
        "read_only": True,
        "status": report.status,
        "run_id": _run_id(report.run_dirs),
        "settings": _report_settings(report.settings),
        "targets": [_report_target(report)],
    }


def _report_settings(settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "hide_completed": bool(settings.get("hide_completed", False)),
        "configured_display_limit": int(settings.get("display_limit", 5)),
        "extra_display_limit": 0,
        "items_per_page": ITEMS_PER_PAGE,
    }


def _report_target(report: ReportData) -> dict[str, Any]:
    display = report.display
    target = {
        key: value
        for key, value in display.items()
        if key not in {"captured", "row_keys"}
    }
    target.update(
        {
            "target_key": _target_label(report.run_dirs),
            "c_saved_artifact": report.saved.count,
            "invariants": {**display["invariants"], "errors": report.errors},
        }
    )
    return target


def _run_id(run_dirs: tuple[Path, ...]) -> str:
    names = {run_dir.name for run_dir in run_dirs}
    return next(iter(names)) if len(names) == 1 else ",".join(sorted(names))


def _target_label(run_dirs: tuple[Path, ...]) -> str:
    labels = {run_dir.parent.name for run_dir in run_dirs}
    return ",".join(sorted(labels))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_arguments(argv)
    report = build_report(
        args.run_dir,
        display_limit=max(1, args.display_limit),
        hide_completed=args.hide_completed,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    _write_report(args.output, rendered)
    return 0 if report["status"] == "measured" else 2


def _parse_arguments(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", action="append", required=True, type=Path)
    parser.add_argument("--display-limit", type=int, default=5)
    parser.add_argument("--hide-completed", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def _write_report(output_path: Path | None, rendered: str) -> None:
    if output_path:
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    raise SystemExit(main())
