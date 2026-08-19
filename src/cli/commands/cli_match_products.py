"""CLI command runner for standalone product matching."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.core.artifact_run import (
    artifact_run,
    artifact_filename,
    current_artifact_run,
)
from src.core.drug_matching.config import (
    MatchingConfig,
)
from src.core.drug_matching.pipeline import MatchPipeline
from src.core.drug_matching.tracing import MatchTraceLog
from src.core.errors import ValidationError
from ..registry import register

logger = logging.getLogger(__name__)


def _match_profile(args: argparse.Namespace) -> str:
    """Return the artifact profile key for standalone matching."""
    return str(args.profile or "default")


def _default_output_path() -> str | None:
    """Return the default run-scoped match-products output path."""
    run = current_artifact_run()
    if not run:
        return None
    return str(run.directory / artifact_filename("match_products", ".csv"))


def _pipeline_from_args(args: argparse.Namespace) -> MatchPipeline:
    """Build MatchPipeline from command-line arguments."""
    cfg = _matching_config(args)
    start, end = _resume_range(args)
    pipeline = MatchPipeline(
        cfg=cfg,
        limit=args.limit,
        start=start,
        end=end,
    )
    if args.trace:
        run = current_artifact_run()
        pipeline._trace = MatchTraceLog(
            log_dir=str(run.directory) if run else None, enabled=True
    )
    return pipeline


def _matching_config(args: argparse.Namespace) -> MatchingConfig:
    """Build MatchingConfig from command-line arguments."""
    return MatchingConfig(
        fuzzy_threshold=args.threshold,
    )


def _resume_range(args: argparse.Namespace) -> tuple[int | None, int | None]:
    """Calculate resume range for pipeline execution."""
    if not args.resume:
        return args.start, args.end
    progress = MatchPipeline.load_progress()
    return (progress["last_end"], args.end) if progress else (args.start, args.end)


def _run_pipeline(pipeline: MatchPipeline, args: argparse.Namespace):
    """Execute the match pipeline with arguments."""
    drugs_path = str(Path(args.excel))
    tawreed_path = str(_tawreed_products_path(args))
    return pipeline.run_full(
        drugs_path=drugs_path,
        tawreed_path=tawreed_path,
        output_path=args.output or _default_output_path(),
    )


def _tawreed_products_path(args: argparse.Namespace) -> Path:
    """Resolve Tawreed products CSV path from arguments."""
    if args.tawreed_csv:
        return Path(args.tawreed_csv)
    if args.profile:
        path = _latest_tawreed_catalog(str(args.profile))
        if path:
            return path
    raise ValidationError(
        "Provide --tawreed-csv or --profile for match-products.",
        hint="Re-run the command with one of these flags.",
        )


def _latest_tawreed_catalog(profile_key: str) -> Path | None:
    """Return the newest Tawreed catalog from new, old, or legacy layouts."""
    paths = list(
        Path("artifacts/export-products").glob(f"{profile_key}/*/tawreed_products*.csv")
    )
    paths.append(Path("artifacts") / profile_key / "tawreed_products.csv")
    paths.extend(Path("artifacts/legacy").glob(f"{profile_key}/*/tawreed_products.csv"))
    existing = [path for path in paths if path.exists()]
    return max(existing, key=lambda path: path.stat().st_mtime) if existing else None


@register("match-products")
def run_match_products_command(app_config, args: argparse.Namespace) -> int:
    """Run standalone matching against an exported Tawreed products CSV.

    The root logger has already been configured by ``run.main()``, so
    this command does not need to install its own handlers — it just
    uses the matching-scoped logger that inherits from root.
    """
    from ..cli_shared import (
        CommandTimer,
        format_duration,
        is_quiet,
        print_command_summary,
    )

    matching_logger = logging.getLogger(__name__)
    timer = CommandTimer()
    matched_count = 0
    total_count = 0
    saved_path: str | None = None
    with timer:
        with artifact_run("match-products", _match_profile(args)) as run:
            matching_logger.info(
                "artifact run started",
                extra={"profile": run.profile_key, "directory": str(run.directory)},
            )
            pipeline = _pipeline_from_args(args)
            matching_logger.info("starting product matching")
            results = _run_pipeline(pipeline, args)
            total_count = len(results)
            if "matched_product_name_en" in results.columns:
                matched_count = int(
                    (results["matched_product_name_en"].fillna("") != "").sum()
                )
            saved_path = str(args.output or _default_output_path() or "")
            matching_logger.info("matched rows", extra={"count": matched_count})

    print_command_summary(
        "match-products",
        {
            "processed": total_count,
            "matched": matched_count,
            "unmatched": total_count - matched_count,
            "duration": format_duration(timer.seconds),
            "summary": saved_path or None,
        },
        success=True,
        quiet=is_quiet(args),
    )
    return 0


__all__ = [
    "run_match_products_command",
    "_pipeline_from_args",
    "_matching_config",
    "_resume_range",
    "_run_pipeline",
    "_tawreed_products_path",
    "_latest_tawreed_catalog",
    "_default_output_path",
    "_match_profile",
]
