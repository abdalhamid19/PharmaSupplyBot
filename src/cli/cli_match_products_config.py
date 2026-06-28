"""Configuration building for match products command."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..core.drug_matching.ai_rotation import configured_attempts
from ..core.drug_matching.config import APIConfig, MatchingConfig, resolve_api_config
from ..core.drug_matching.pipeline import MatchPipeline
from ..core.drug_matching.trace_log import MatchTraceLog
from ..core.artifact_run import current_artifact_run, artifact_filename
from .cli_match_products_helpers import _search_policy_values


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
        pipeline._trace = MatchTraceLog(log_dir=str(run.directory) if run else None, enabled=True)
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
    """Calculate resume range for pipeline execution."""
    if not args.resume:
        return args.start, args.end
    progress = MatchPipeline.load_progress()
    return (progress["last_end"], args.end) if progress else (args.start, args.end)


__all__ = [
    "_pipeline_from_args",
    "_matching_config",
    "_api_config",
    "_rotation_api_config",
    "_resolved_api_config",
    "_resume_range",
]
