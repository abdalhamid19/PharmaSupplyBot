"""Configuration loading and profile selection for the Tawreed bot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_BASE_URL = "https://seller.tawreed.io/#/login"
DEFAULT_CODE_COLUMN = "ÙƒÙˆØ¯"
DEFAULT_NAME_COLUMN = "Ø¥Ø³Ù… Ø§Ù„ØµÙ†Ù"
DEFAULT_QUANTITY_COLUMN = "ÙƒÙ…ÙŠØ© Ø§Ù„Ù†Ù‚Øµ"


@dataclass(frozen=True)
class ExcelConfig:
    """Excel column names and quantity bounds used to load shortage items."""

    code_col: str
    name_col: str
    qty_col: str
    min_qty: int = 1
    max_qty: int = 10**9


@dataclass(frozen=True)
class ProfileConfig:
    """One pharmacy profile plus its optional pharmacy-switch settings."""

    display_name: str
    pharmacy_switch: dict[str, Any]


@dataclass(frozen=True)
class RuntimeConfig:
    """Browser runtime settings shared across auth and ordering flows."""

    headless: bool = True
    slow_mo_ms: int = 0
    timeout_ms: int = 45000


@dataclass(frozen=True)
class MatchingConfig:
    """Thresholds that decide whether a Tawreed product match is acceptable."""

    exact_match_accept: bool = True
    high_overlap_threshold: float = 0.85
    medium_score_threshold: float = 12.0
    medium_overlap_threshold: float = 0.6
    numeric_score_threshold: float = 16.0
    numeric_overlap_threshold: float = 0.45


@dataclass(frozen=True)
class AppConfig:
    """Fully parsed application configuration consumed by the bot."""

    base_url: str
    excel: ExcelConfig
    profiles: dict[str, ProfileConfig]
    selectors: dict[str, Any]
    warehouse_strategy: dict[str, Any]
    matching: MatchingConfig
    runtime: RuntimeConfig

    def profiles_to_run(
        self,
        profile: str | None,
        all_profiles: bool,
    ) -> list[tuple[str, ProfileConfig]]:
        """Return the configured profiles requested by the CLI arguments."""
        if all_profiles:
            return list(self.profiles.items())
        if profile:
            return self._selected_profile(profile)
        if len(self.profiles) == 1:
            profile_key = next(iter(self.profiles.keys()))
            return [(profile_key, self.profiles[profile_key])]
        raise SystemExit("Please provide --profile <name> or use --all-profiles")

    def _selected_profile(self, profile: str) -> list[tuple[str, ProfileConfig]]:
        """Return one explicitly selected profile or raise a descriptive error."""
        if profile not in self.profiles:
            available_profiles = ", ".join(self.profiles.keys())
            raise KeyError(
                f"Unknown profile '{profile}'. Available: {available_profiles}"
            )
        return [(profile, self.profiles[profile])]


def load_config(path: Path) -> AppConfig:
    """Load application settings from a YAML configuration file."""
    raw_values = _load_raw_config(path)
    site_values = _require(raw_values, "site")
    excel_values = _require(raw_values, "excel")
    profiles_values = _require(raw_values, "profiles")
    return AppConfig(
        base_url=str(site_values.get("base_url", DEFAULT_BASE_URL)),
        excel=_build_excel_config(excel_values),
        profiles=_build_profiles(profiles_values),
        selectors=dict(raw_values.get("selectors", {})),
        warehouse_strategy=dict(raw_values.get("warehouse_strategy", {})),
        matching=_build_matching_config(raw_values),
        runtime=_build_runtime_config(raw_values),
    )


def _build_excel_config(excel_values: dict[str, Any]) -> ExcelConfig:
    """Build Excel column settings from the raw YAML dictionary."""
    return ExcelConfig(
        code_col=str(excel_values.get("code_col", DEFAULT_CODE_COLUMN)),
        name_col=str(excel_values.get("name_col", DEFAULT_NAME_COLUMN)),
        qty_col=str(excel_values.get("qty_col", DEFAULT_QUANTITY_COLUMN)),
        min_qty=int(excel_values.get("min_qty", 1)),
        max_qty=int(excel_values.get("max_qty", 10**9)),
    )


def _build_profiles(profiles_values: dict[str, Any]) -> dict[str, ProfileConfig]:
    """Build profile objects from the raw YAML dictionary."""
    profiles: dict[str, ProfileConfig] = {}
    for profile_key, profile_values in profiles_values.items():
        profiles[profile_key] = _build_profile(profile_key, profile_values)
    return profiles


def _build_profile(profile_key: str, profile_values: dict[str, Any]) -> ProfileConfig:
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


def _build_runtime_config(raw_values: dict[str, Any]) -> RuntimeConfig:
    """Build runtime settings from the optional YAML section."""
    runtime_values = dict(raw_values.get("runtime", {}))
    return RuntimeConfig(
        headless=bool(runtime_values.get("headless", True)),
        slow_mo_ms=int(runtime_values.get("slow_mo_ms", 0)),
        timeout_ms=int(runtime_values.get("timeout_ms", 45000)),
    )


def _build_matching_config(raw_values: dict[str, Any]) -> MatchingConfig:
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


def _load_raw_config(path: Path) -> dict[str, Any]:
    """Read the YAML configuration file from disk."""
    if not path.exists():
        raise FileNotFoundError(
            "Config file not found: "
            f"{path}. Create it by copying config.example.yaml to config.yaml"
        )
    raw_values = yaml.safe_load(path.read_text(encoding="utf-8"))
    _require(raw_values, "site")
    _require(raw_values, "excel")
    _require(raw_values, "profiles")
    return raw_values


def _require(values: dict[str, Any], key: str) -> Any:
    """Return a required config key or raise a descriptive error."""
    if key not in values:
        raise KeyError(f"Missing required config key: {key}")
    return values[key]
