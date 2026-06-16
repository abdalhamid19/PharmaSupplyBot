"""Builder helpers for converting raw YAML values into configuration dataclasses."""

from __future__ import annotations

from typing import Any

from .config_models import ExcelConfig, MatchingConfig, ProfileConfig, RuntimeConfig

DEFAULT_BASE_URL = "https://seller.tawreed.io/#/login"
DEFAULT_CODE_COLUMN = "كود"
DEFAULT_NAME_COLUMN = "إسم الصنف"
DEFAULT_QUANTITY_COLUMN = "كمية النقص"


def build_excel_config(excel_values: dict[str, Any]) -> ExcelConfig:
    """Build Excel column settings from the raw YAML dictionary."""
    return ExcelConfig(
        code_col=str(excel_values.get("code_col", DEFAULT_CODE_COLUMN)),
        name_col=str(excel_values.get("name_col", DEFAULT_NAME_COLUMN)),
        qty_col=str(excel_values.get("qty_col", DEFAULT_QUANTITY_COLUMN)),
        min_qty=int(excel_values.get("min_qty", 1)),
        max_qty=int(excel_values.get("max_qty", 10**9)),
    )


def build_profiles(profiles_values: dict[str, Any]) -> dict[str, ProfileConfig]:
    """Build profile objects from the raw YAML dictionary."""
    profiles: dict[str, ProfileConfig] = {}
    for profile_key, profile_values in profiles_values.items():
        profiles[profile_key] = build_profile(profile_key, profile_values)
    return profiles


def build_profile(profile_key: str, profile_values: dict[str, Any]) -> ProfileConfig:
    """Build one profile object from the raw YAML dictionary."""
    return ProfileConfig(
        display_name=str(profile_values.get("display_name", profile_key)),
        pharmacy_switch=dict(
            profile_values.get(
                "pharmacy_switch",
                {"enabled": False, "pharmacy_name": ""},
            )
        ),
    )


def build_runtime_config(raw_values: dict[str, Any]) -> RuntimeConfig:
    """Build runtime settings from the optional YAML section."""
    runtime_values = dict(raw_values.get("runtime", {}))
    return RuntimeConfig(
        headless=bool(runtime_values.get("headless", True)),
        slow_mo_ms=int(runtime_values.get("slow_mo_ms", 0)),
        timeout_ms=int(runtime_values.get("timeout_ms", 45000)),
        submit_order=bool(runtime_values.get("submit_order", False)),
        max_workers=int(runtime_values.get("max_workers", 1)),
        item_workers=int(runtime_values.get("item_workers", 1)),
    )


def build_matching_config(raw_values: dict[str, Any]) -> MatchingConfig:
    """Build product-matching thresholds from the optional YAML section."""
    matching_values = dict(raw_values.get("matching", {}))
    default_config = MatchingConfig()
    kwargs = _matching_float_values(matching_values, default_config)
    for k in (
        "exact_match_accept",
        "candidate_top_k",
        "fuzzy_prefix_len",
        "query_cache_size",
        "require_identity_token_for_flag",
    ):
        val = _matching_value(matching_values, default_config, k)
        if k in {"exact_match_accept", "require_identity_token_for_flag"}:
            kwargs[k] = bool(val)
        else:
            kwargs[k] = int(val)
    return MatchingConfig(**kwargs)


def _matching_float_values(
    matching_values: dict[str, Any], default_config: MatchingConfig
) -> dict[str, float]:
    """Return all float matching settings parsed from raw config."""
    names = (
        "high_overlap_threshold",
        "medium_score_threshold",
        "medium_overlap_threshold",
        "numeric_score_threshold",
        "numeric_overlap_threshold",
        "numeric_score_weight",
        "critical_token_penalty",
        "distinguishing_token_penalty",
        "semantic_mismatch_penalty",
        "early_stop_confidence",
    )
    return {
        n: float(_matching_value(matching_values, default_config, n)) for n in names
    }


def _matching_value(matching_values, default_config: MatchingConfig, name: str) -> Any:
    """Return one configured matching value with dataclass defaults."""
    return matching_values.get(name, getattr(default_config, name))
