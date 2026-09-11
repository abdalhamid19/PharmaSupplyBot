"""Build a read-only manifest for an Excel-target replay.

The manifest makes a before/after comparison auditable.  It fingerprints the
code/configuration, input workbooks, state databases, and canonicalized target
catalog rows without opening any database in write mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config.config import load_config
from src.core.excel_target.approved_correction_analysis import catalog_fingerprint
from src.core.excel_target.excel_target_loader import load_target_catalog_from_excel


DEFAULT_DEPENDENCY_FILES = (
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
)


@dataclass(frozen=True)
class ReplayManifestInputs:
    """Explicit read-only inputs used to build one replay manifest."""

    config_path: Path
    order_workbook: Path
    catalog_paths: Mapping[str, Path]
    prevented_workbook: Path | None = None
    manual_review_db: Path | None = None
    order_runs_db: Path | None = None
    run_id: str = ""
    command_line: str = ""


def sha256_file(path: Path | None) -> str | None:
    """Return a file digest, or ``None`` when the optional file is absent."""
    if path is None or not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _sha256_bytes(parts: Iterable[bytes]) -> str:
    """Hash a sequence of labeled byte fragments."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
    return digest.hexdigest().upper()


def _git(*args: str) -> str:
    """Return one git command's UTF-8 output without changing the worktree."""
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return completed.stdout.decode("utf-8", errors="replace").strip()


def working_tree_patch_sha256() -> str:
    """Fingerprint tracked changes and untracked path names in the worktree."""
    status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    return _sha256_bytes((b"status\0", status, b"diff\0", diff))


def dependency_lock_sha256() -> str | None:
    """Hash the available dependency declaration files by name and content."""
    files = [ROOT / name for name in DEFAULT_DEPENDENCY_FILES if (ROOT / name).exists()]
    if not files:
        return None
    parts: list[bytes] = []
    for path in files:
        parts.extend((path.name.encode("utf-8"), b"\0", path.read_bytes(), b"\0"))
    return _sha256_bytes(parts)


def _catalog_fingerprints(
    config_path: Path,
    catalog_paths: Mapping[str, Path],
) -> dict[str, str]:
    """Load each target catalog and fingerprint canonicalized identity rows."""
    app_config = load_config(config_path)
    fingerprints: dict[str, str] = {}
    for target_key, catalog_path in sorted(catalog_paths.items()):
        target_config = app_config.excel_targets.get(target_key)
        if target_config is None:
            raise KeyError(f"Target '{target_key}' is not configured in {config_path}")
        catalog = load_target_catalog_from_excel(
            catalog_path,
            target_config,
            source_file=catalog_path.name,
        )
        fingerprints[target_key] = catalog_fingerprint(target_key, catalog)
    return fingerprints


def _manifest_file_hashes(inputs: ReplayManifestInputs) -> dict[str, object]:
    """Hash replay files without opening any state database for writes."""
    catalog_hashes = {
        target: sha256_file(path)
        for target, path in sorted(inputs.catalog_paths.items())
    }
    return {
        "config_sha256": sha256_file(inputs.config_path),
        "order_workbook_sha256": sha256_file(inputs.order_workbook),
        "catalog_workbook_sha256": catalog_hashes,
        "prevented_workbook_sha256": sha256_file(inputs.prevented_workbook),
        "manual_review_db_sha256": sha256_file(inputs.manual_review_db),
        "order_runs_db_sha256": sha256_file(inputs.order_runs_db),
    }


def build_manifest(inputs: ReplayManifestInputs) -> dict[str, object]:
    """Build a read-only replay manifest from explicit input paths."""
    file_hashes = _manifest_file_hashes(inputs)
    return {
        "manifest_version": 1,
        "run_id": str(inputs.run_id),
        "git_sha": _git("rev-parse", "HEAD"),
        "working_tree_patch_sha256": working_tree_patch_sha256(),
        "python_version": platform.python_version(),
        "dependency_lock_sha256": dependency_lock_sha256(),
        **file_hashes,
        "target_catalog_fingerprint": _catalog_fingerprints(
            inputs.config_path, inputs.catalog_paths
        ),
        "command_line": str(inputs.command_line),
    }


def _path(value: str) -> Path:
    """Resolve a CLI path relative to the repository root."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _catalog_arg(value: str) -> tuple[str, Path]:
    """Parse ``TARGET=PATH`` from a repeated ``--catalog`` argument."""
    target_key, separator, path = value.partition("=")
    if not separator or not target_key.strip() or not path.strip():
        raise argparse.ArgumentTypeError("catalog must be TARGET=PATH")
    return target_key.strip(), _path(path.strip())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse manifest CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="state/config.yaml", type=_path)
    parser.add_argument("--order-workbook", required=True, type=_path)
    parser.add_argument("--catalog", action="append", required=True, type=_catalog_arg)
    parser.add_argument("--prevented-workbook", type=_path)
    parser.add_argument("--manual-review-db", type=_path)
    parser.add_argument("--order-runs-db", type=_path)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--command-line", default="")
    parser.add_argument("--output", required=True, type=_path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Build and write one JSON manifest."""
    args = parse_args(argv)
    catalog_paths = dict(args.catalog)
    manifest = build_manifest(
        ReplayManifestInputs(
            config_path=args.config,
            order_workbook=args.order_workbook,
            catalog_paths=catalog_paths,
            prevented_workbook=args.prevented_workbook,
            manual_review_db=args.manual_review_db,
            order_runs_db=args.order_runs_db,
            run_id=args.run_id,
            command_line=args.command_line,
        )
    )
    _write_manifest(args.output, manifest)
    return 0


def _write_manifest(output_path: Path, manifest: dict[str, object]) -> None:
    """Write one JSON manifest and no other artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
