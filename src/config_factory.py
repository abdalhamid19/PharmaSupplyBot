"""Builder helpers for converting raw YAML values into configuration dataclasses."""

from __future__ import annotations

from typing import Any

from .config_models import ExcelConfig, MatchingConfig, ProfileConfig, RuntimeConfig


DEFAULT_BASE_URL = "https://seller.tawreed.io/#/login"
DEFAULT_CODE_COLUMN = "Ã™Æ’Ã™Ë†Ã˜Â¯"
DEFAULT_NAME_COLUMN = "Ã˜Â¥Ã˜Â³Ã™â€¦ Ã˜Â§Ã™â€žÃ˜ÂµÃ™â€ Ã™Â"
DEFAULT_QUANTITY_COLUMN = "Ã™Æ’Ã™â€¦Ã™Å Ã˜Â© Ã˜Â§Ã™â€žÃ™â€ Ã™â€šÃ˜Âµ"


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
    )


def build_matching_config(raw_values: dict[str, Any]) -> MatchingConfig:
    """Build product-matching thresholds from the optional YAML section."""
    matching_values = dict(raw_values.get("matching", {}))
    return MatchingConfig(
        exact_match_accept=bool(matching_values.get("exact_match_accept", True)),
        high_overlap_threshold=float(matching_values.get("high_overlap_threshold", 0.85)),
        medium_score_threshold=float(matching_values.get("medium_score_threshold", 12.0)),
        medium_overlap_threshold=float(matching_values.get("medium_overlap_threshold", 0.6)),
        numeric_score_threshold=float(matching_values.get("numeric_score_threshold", 16.0)),
        numeric_overlap_threshold=float(matching_values.get("numeric_overlap_threshold", 0.45)),
    )
