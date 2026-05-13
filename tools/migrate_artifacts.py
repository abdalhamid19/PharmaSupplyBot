"""Move legacy flat artifacts into command-oriented run folders."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

COMMAND_DIRS = {
    "order",
    "match-products",
    "export-products",
    "remove-cart",
    "run-control",
    "legacy",
}


def migrate_artifacts(root: Path = Path("artifacts"), stamp: str | None = None) -> None:
    """Move old artifact layouts under artifacts/legacy and preserve catalogs."""
    if not root.exists():
        return
    migration_id = stamp or datetime.now().strftime("%Y%m%d_%H%M")
    for profile_dir in _legacy_profile_dirs(root):
        _move_profile_dir(root, profile_dir, migration_id)
    _move_named_dir(root, "matching", root / "legacy/matching" / migration_id)
    _move_named_dir(root, "run_control", root / "legacy/run_control" / migration_id)


def _legacy_profile_dirs(root: Path) -> list[Path]:
    return [
        path for path in root.iterdir()
        if path.is_dir() and path.name not in COMMAND_DIRS and path.name != "matching"
    ]


def _move_profile_dir(root: Path, profile_dir: Path, migration_id: str) -> None:
    target = root / "legacy" / profile_dir.name / migration_id
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target = target.with_name(f"{target.name}_2")
    shutil.move(str(profile_dir), str(target))
    _preserve_catalog(root, profile_dir.name, target, migration_id)


def _preserve_catalog(
    root: Path, profile_key: str, legacy_dir: Path, migration_id: str
) -> None:
    catalog = legacy_dir / "tawreed_products.csv"
    if not catalog.exists():
        return
    export_dir = root / "export-products" / profile_key / migration_id
    export_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(catalog, export_dir / f"tawreed_products_{migration_id}.csv")


def _move_named_dir(root: Path, name: str, target: Path) -> None:
    source = root / name
    if not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))


if __name__ == "__main__":
    migrate_artifacts()
