"""Main command runner for standalone product matching."""

from __future__ import annotations

import argparse
import asyncio

from ..core.artifact_run import artifact_run, current_artifact_run
from ..core.matching_trace import configure_async_logging
from .cli_match_products_config import _pipeline_from_args
from .cli_match_products_execution import _run_pipeline
from .cli_match_products_helpers import _match_profile


def run_match_products_command(app_config, args: argparse.Namespace) -> int:
    """Run standalone matching against an exported Tawreed products CSV."""
    from ..core.drug_matching.config import load_env, setup_logging
    load_env()
    setup_logging("INFO")
    logger, listener = configure_async_logging("INFO")
    try:
        with artifact_run("match-products", _match_profile(args)) as run:
            print(f"[{run.profile_key}] Artifact run: {run.directory}")
            pipeline = _pipeline_from_args(args)
            logger.info("Starting product matching")
            results = asyncio.run(_run_pipeline(pipeline, args))
            logger.info("Matched %s rows", len(results))
    finally:
        listener.stop()
    return 0


__all__ = ["run_match_products_command"]
