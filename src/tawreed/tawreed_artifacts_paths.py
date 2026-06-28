"""Path helpers for Tawreed artifact management."""

from __future__ import annotations

from pathlib import Path

from ..core.artifact_run import artifact_filename, current_artifact_run


def _artifact_path(
    profile_key: str, label: str, label_suffix: str | None, extension: str
) -> Path:
    """Return the fully-qualified artifact path for one label."""
    active = current_artifact_run()
    if active:
        parent = active.directory / _active_artifact_subdir(label, extension)
        parent.mkdir(parents=True, exist_ok=True)
        return parent / artifact_filename(label, extension, label_suffix)
    effective_label = f"{label}.{label_suffix}" if label_suffix else label
    return _artifacts_dir(profile_key) / f"{effective_label}{extension}"


def _active_artifact_subdir(label: str, extension: str) -> Path:
    """Return the run-local grouping directory for noisy diagnostic artifacts."""
    if label.startswith("match_log"):
        return Path("logs") / "match"
    if extension == ".html":
        return Path("diagnostics") / "html"
    if extension == ".png":
        return Path("diagnostics") / "images"
    if label.endswith("_error") or "error" in label:
        return Path("diagnostics") / "errors"
    return Path()


def _artifacts_dir(profile_key: str) -> Path:
    """Return the artifacts directory for the active profile, creating it if needed."""
    active = current_artifact_run()
    artifacts_dir = active.directory if active else Path("artifacts") / profile_key
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir
