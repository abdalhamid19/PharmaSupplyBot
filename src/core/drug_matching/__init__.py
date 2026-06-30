"""Drug Matcher - High-performance drug name matching pipeline."""

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

__version__ = "2.0.0"
