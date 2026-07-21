"""CLI command runner for standalone product matching."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from src.core.artifact_run import (
    artifact_run,
    artifact_filename,
    current_artifact_run,
)
from src.core.drug_matching.ai.ai_rotation import configured_attempts
from src.core.drug_matching.config import (
    APIConfig,
    MatchingConfig,
    load_env,
    resolve_api_config,
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


def _search_policy_values(args: argparse.Namespace) -> tuple[float, float, int]:
    """Return search policy defaults based on policy name."""
    defaults = {
        "safe": (80.0, 0.75, 5),
        "review-candidates": (80.0, 0.75, 8),
        "expanded": (75.0, 0.75, 10),
        "aggressive": (70.0, 0.75, 15),
    }
    return defaults[str(args.ai_search_policy)]


def _pipeline_from_args(args: argparse.Namespace) -> MatchPipeline:
    """Build MatchPipeline from command-line arguments."""
    cfg = _matching_config(args)
    api_cfg = _api_config(args)
    start, end = _resume_range(args)
    pipeline = MatchPipeline(
        cfg=cfg,
        api_cfg=api_cfg,
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
    concurrency = max(1, int(args.concurrency or 5))
    min_score, confidence, candidate_limit = _search_policy_values(args)
    return MatchingConfig(
        fuzzy_threshold=args.threshold,
        ai_verify_threshold=args.ai_threshold,
        ai_verify_policy=args.ai_verify_policy,
        ai_max_concurrent=concurrency,
        ai_search_policy=args.ai_search_policy,
        ai_search_limit=args.ai_search_limit,
        ai_search_min_candidate_score=min_score,
        ai_search_accept_confidence=confidence,
        ai_search_candidate_limit=candidate_limit,
    )


def _api_config(args: argparse.Namespace) -> APIConfig:
    """Build APIConfig from command-line arguments."""
    if args.provider == "rotation":
        return _rotation_api_config(args)
    return _resolved_api_config(args)


def _rotation_api_config(args: argparse.Namespace) -> APIConfig:
    """Build APIConfig for rotation mode."""
    attempts = configured_attempts("auto")
    first = attempts[0] if attempts else None
    return APIConfig(
        api_key=first.api_key if first else "",
        api_keys=(first.api_key,) if first else (),
        base_url=first.base_url if first else "",
        model=first.model if first else "",
        review_model=args.review_model or "",
        attempt_plan=attempts,
    )


def _resolved_api_config(args: argparse.Namespace) -> APIConfig:
    """Build APIConfig for resolved provider."""
    resolved = resolve_api_config(
        args.provider or "", args.model or "", args.api_key or ""
    )
    return APIConfig(
        api_key=resolved["api_key"],
        api_keys=resolved.get("api_keys", ()),
        base_url=resolved["base_url"],
        model=resolved["model"],
        fallback_models=resolved.get("fallback_models", ()),
        review_model=args.review_model or "",
        max_tokens=512,
        temperature=0.1,
    )


def _resume_range(args: argparse.Namespace) -> tuple[int | None, int | None]:
    """Calculate resume range for pipeline execution."""
    if not args.resume:
        return args.start, args.end
    progress = MatchPipeline.load_progress()
    return (progress["last_end"], args.end) if progress else (args.start, args.end)


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
    load_env()
    matching_logger = logging.getLogger(__name__)
    with artifact_run("match-products", _match_profile(args)) as run:
        matching_logger.info(
            "artifact run started",
            extra={"profile": run.profile_key, "directory": str(run.directory)},
        )
        pipeline = _pipeline_from_args(args)
        matching_logger.info("starting product matching")
        results = asyncio.run(_run_pipeline(pipeline, args))
        matching_logger.info("matched rows", extra={"count": len(results)})
    return 0


__all__ = [
    "run_match_products_command",
    "_pipeline_from_args",
    "_matching_config",
    "_api_config",
    "_rotation_api_config",
    "_resolved_api_config",
    "_resume_range",
    "_run_pipeline",
    "_tawreed_products_path",
    "_latest_tawreed_catalog",
    "_default_output_path",
    "_match_profile",
    "_search_policy_values",
]
