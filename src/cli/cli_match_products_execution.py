"""Pipeline execution for match products command."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from ..core.drug_matching.pipeline import MatchPipeline
from .cli_match_products_helpers import _default_output_path


async def _run_pipeline(pipeline: MatchPipeline, args: argparse.Namespace):
    """Execute the match pipeline with arguments."""
    drugs_path = str(Path(args.excel))
    tawreed_path = str(_tawreed_products_path(args))
    return await pipeline.run_full(
        drugs_path=drugs_path,
        tawreed_path=tawreed_path,
        output_path=args.output or _default_output_path(),
        skip_ai=bool(args.no_ai),
    )


def _tawreed_products_path(args: argparse.Namespace) -> Path:
    """Resolve Tawreed products CSV path from arguments."""
    if args.tawreed_csv:
        return Path(args.tawreed_csv)
    if args.profile:
        path = _latest_tawreed_catalog(str(args.profile))
        if path:
            return path
    raise SystemExit("Provide --tawreed-csv or --profile for match-products.")


def _latest_tawreed_catalog(profile_key: str) -> Path | None:
    """Return the newest Tawreed catalog from new, old, or legacy layouts."""
    paths = list(Path("artifacts/export-products").glob(f"{profile_key}/*/tawreed_products*.csv"))
    paths.append(Path("artifacts") / profile_key / "tawreed_products.csv")
    paths.extend(Path("artifacts/legacy").glob(f"{profile_key}/*/tawreed_products.csv"))
    existing = [path for path in paths if path.exists()]
    return max(existing, key=lambda path: path.stat().st_mtime) if existing else None


def _default_output_path() -> str | None:
    """Return the default run-scoped match-products output path."""
    from ..core.artifact_run import current_artifact_run, artifact_filename
    run = current_artifact_run()
    if not run:
        return None
    return str(run.directory / artifact_filename("match_products", ".csv"))


__all__ = [
    "_run_pipeline",
    "_tawreed_products_path",
    "_latest_tawreed_catalog",
    "_default_output_path",
]
