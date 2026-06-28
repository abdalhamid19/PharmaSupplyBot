"""Helper functions for match products command."""

from __future__ import annotations

import argparse

from ..core.artifact_run import current_artifact_run, artifact_filename


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


__all__ = ["_match_profile", "_default_output_path", "_search_policy_values"]
