"""Summary and artifact-related functions for order items."""

from __future__ import annotations

import csv
from pathlib import Path

from ..tawreed.tawreed_match_only import MATCH_ONLY_SUMMARY_LABEL
from ..core.artifact_run import current_artifact_run


def summary_label(args) -> str:
    """Return the canonical summary label for the requested order mode."""
    if bool(getattr(args, "match_only", False)):
        return MATCH_ONLY_SUMMARY_LABEL
    return "order_item_summary"


def processed_summary_item_keys(
    profile_key: str, summary_label: str = "order_item_summary"
) -> set[tuple[str, str]]:
    """Return item keys already written to the active profile summary."""
    summary_path = latest_summary_path(profile_key, summary_label)
    if summary_path is None:
        return set()
    with summary_path.open("r", encoding="utf-8", newline="") as summary_file:
        reader = csv.DictReader(summary_file)
        return {
            item_key(row.get("item_code", ""), row.get("item_name", ""))
            for row in reader
        }


def latest_summary_path(profile_key: str, summary_label: str) -> Path | None:
    """Return the newest summary path from active, command, or legacy layouts."""
    active = current_artifact_run()
    paths: list[Path] = []
    if active:
        paths.extend(active.directory.glob(f"{summary_label}*.csv"))
    paths.extend(Path("artifacts/order").glob(f"{profile_key}/*/{summary_label}*.csv"))
    paths.append(Path("artifacts") / profile_key / f"{summary_label}.csv")
    paths.extend(Path("artifacts/legacy").glob(f"{profile_key}/*/{summary_label}*.csv"))
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def item_key(code: object, name: object) -> tuple[str, str]:
    """Return a stable key for matching Excel items to summary rows."""
    normalized_code = str(code or "").strip().lower()
    normalized_name = str(name or "").strip().lower()
    if normalized_code in {"", "nan", "none"}:
        normalized_code = ""
    return normalized_code, normalized_name


__all__ = [
    "summary_label",
    "processed_summary_item_keys",
    "latest_summary_path",
    "item_key",
]
