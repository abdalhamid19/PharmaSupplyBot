"""Configuration module for drug matching.

This module provides configuration models, helpers, and provider settings
for AI API integration and drug matching parameters.
"""

from .config import (
    ROOT_DIR,
    MatchingConfig,
    APIConfig,
    Paths,
    PROVIDERS,
    provider_base_url,
    cloudflare_base_url,
    setup_logging,
    load_env,
    resolve_api_config,
    _default_output_csv,
    _provider_api_config,
    _load_env_line,
    _configured_env_key_values,
    _fallback_models,
    _dedupe,
)

__all__ = [
    "ROOT_DIR",
    "MatchingConfig",
    "APIConfig",
    "Paths",
    "PROVIDERS",
    "provider_base_url",
    "cloudflare_base_url",
    "setup_logging",
    "load_env",
    "resolve_api_config",
    "_default_output_csv",
    "_provider_api_config",
    "_load_env_line",
    "_configured_env_key_values",
    "_fallback_models",
    "_dedupe",
]
