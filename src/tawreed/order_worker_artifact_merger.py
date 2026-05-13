"""Merge order worker AI trace, summary, and manual-review artifacts."""

from __future__ import annotations

from pathlib import Path

from ..core.artifact_run import artifact_filename, current_artifact_run
from .order_result_merger import merge_worker_summaries


def merge_order_worker_artifacts(profile_key: str, labels: tuple[str, ...]) -> None:
    """Merge worker CSV and TXT partitions for order-run labels."""
    for label in labels:
        merge_worker_summaries(profile_key, label)
        _merge_worker_text(profile_key, label)


def _merge_worker_text(profile_key: str, label: str) -> None:
    directory = _artifact_directory(profile_key)
    paths = _worker_text_paths(directory, label)
    if not paths:
        return
    target = _target_text_path(directory, label)
    with target.open("w", encoding="utf-8") as output:
        for path in paths:
            output.write(path.read_text(encoding="utf-8"))
    _remove_worker_text(paths)


def _artifact_directory(profile_key: str) -> Path:
    active = current_artifact_run()
    directory = active.directory if active else Path("artifacts") / profile_key
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _worker_text_paths(directory: Path, label: str) -> list[Path]:
    patterns = (f"{label}.worker_*.txt", f"{label}_worker_*.txt")
    return sorted(path for pattern in patterns for path in directory.glob(pattern))


def _target_text_path(directory: Path, label: str) -> Path:
    if current_artifact_run():
        return directory / artifact_filename(label, ".txt")
    return directory / f"{label}.txt"


def _remove_worker_text(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink()
        except Exception:
            pass
