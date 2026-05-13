"""Run-scoped artifact paths for CLI, Tawreed, and Streamlit workflows."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

ARTIFACT_ROOT = Path("artifacts")
RUN_ID_FORMAT = "%Y%m%d_%H%M"

_CURRENT_RUN: ContextVar["ArtifactRun | None"] = ContextVar("artifact_run", default=None)

@dataclass(frozen=True)
class ArtifactRun:
    """Identify one command/profile output directory."""

    command: str
    profile_key: str
    run_id: str
    root: Path = ARTIFACT_ROOT

    @property
    def directory(self) -> Path:
        """Return the concrete artifact directory for this run."""
        return self.root / self.command / self.profile_key / self.run_id

def minute_run_id(now: datetime | None = None) -> str:
    """Return a timestamp run id with minute precision."""
    return (now or datetime.now()).strftime(RUN_ID_FORMAT)


def unique_run_id(command: str, profile_key: str, root: Path = ARTIFACT_ROOT) -> str:
    """Return a minute run id that does not collide for this command/profile."""
    base = minute_run_id()
    parent = root / command / profile_key
    return _unique_name(parent, base)

@contextmanager
def artifact_run(
    command: str,
    profile_key: str,
    run_id: str | None = None,
    root: Path = ARTIFACT_ROOT,
) -> Iterator[ArtifactRun]:
    """Activate a run-scoped artifact context within the current execution path."""
    active_run_id = run_id or unique_run_id(command, profile_key, root)
    active = ArtifactRun(command, profile_key, active_run_id, root)
    active.directory.mkdir(parents=True, exist_ok=True)
    token = _CURRENT_RUN.set(active)
    try:
        yield active
    finally:
        _CURRENT_RUN.reset(token)


def current_artifact_run() -> ArtifactRun | None:
    """Return the active run-scoped artifact context when one is set."""
    return _CURRENT_RUN.get()

def run_control_dir(command: str, root: Path = ARTIFACT_ROOT) -> Path:
    """Return the run-control directory for one command."""
    directory = root / "run-control" / command
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def artifact_filename(label: str, extension: str, suffix: str | None = None) -> str:
    """Return a timestamped artifact file name for the active run."""
    active = current_artifact_run()
    stamp = active.run_id if active else minute_run_id()
    parts = [label]
    if suffix:
        parts.append(suffix)
    parts.append(stamp)
    return "_".join(parts) + extension


def unique_path(path: Path) -> Path:
    """Return a non-existing path by adding a numeric suffix when needed."""
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _unique_name(parent: Path, base: str) -> str:
    candidate = base
    counter = 2
    while (parent / candidate).exists():
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate
