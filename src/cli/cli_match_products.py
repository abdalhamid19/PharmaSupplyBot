"""CLI command runner for standalone product matching."""

from __future__ import annotations

from .cli_match_products_main import run_match_products_command
from .cli_match_products_config import (
    _pipeline_from_args,
    _matching_config,
    _api_config,
    _rotation_api_config,
    _resolved_api_config,
    _resume_range,
)
from .cli_match_products_execution import (
    _run_pipeline,
    _tawreed_products_path,
    _latest_tawreed_catalog,
    _default_output_path,
)
from .cli_match_products_helpers import _match_profile, _search_policy_values


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

