"""CLI command runner for standalone product matching."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from ..core.config.config_models import AppConfig
from ..core.drug_matching.ai_rotation import configured_attempts
from ..core.drug_matching.config import (
    APIConfig,
    MatchingConfig,
    load_env,
    resolve_api_config,
    setup_logging,
)
from ..core.drug_matching.pipeline import MatchPipeline
from ..core.drug_matching.trace_log import MatchTraceLog
from ..core.matching_trace import configure_async_logging


def run_match_products_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Run standalone matching against an exported Tawreed products CSV."""
    load_env()
    setup_logging("INFO")
    logger, listener = configure_async_logging("INFO")
    try:
        pipeline = _pipeline_from_args(args)
        logger.info("Starting product matching")
        results = asyncio.run(_run_pipeline(pipeline, args))
        logger.info("Matched %s rows", len(results))
    finally:
        listener.stop()
    return 0


def _pipeline_from_args(args: argparse.Namespace) -> MatchPipeline:
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
        pipeline._trace = MatchTraceLog(enabled=True)
    return pipeline


async def _run_pipeline(pipeline: MatchPipeline, args: argparse.Namespace):
    drugs_path = str(Path(args.excel))
    tawreed_path = str(_tawreed_products_path(args))
    return await pipeline.run_full(
        drugs_path=drugs_path,
        tawreed_path=tawreed_path,
        output_path=args.output,
        skip_ai=bool(args.no_ai),
    )


def _matching_config(args: argparse.Namespace) -> MatchingConfig:
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
    if args.provider == "rotation":
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
    resolved = resolve_api_config(args.provider or "", args.model or "", args.api_key or "")
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
    if not args.resume:
        return args.start, args.end
    progress = MatchPipeline.load_progress()
    return (progress["last_end"], args.end) if progress else (args.start, args.end)


def _tawreed_products_path(args: argparse.Namespace) -> Path:
    if args.tawreed_csv:
        return Path(args.tawreed_csv)
    if args.profile:
        return Path("artifacts") / str(args.profile) / "tawreed_products.csv"
    raise SystemExit("Provide --tawreed-csv or --profile for match-products.")


def _search_policy_values(args: argparse.Namespace) -> tuple[float, float, int]:
    defaults = {
        "safe": (80.0, 0.75, 5),
        "review-candidates": (80.0, 0.75, 8),
        "expanded": (75.0, 0.75, 10),
        "aggressive": (70.0, 0.75, 15),
    }
    return defaults[str(args.ai_search_policy)]
