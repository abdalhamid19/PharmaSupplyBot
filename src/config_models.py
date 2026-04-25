"""Configuration dataclasses used by the Tawreed bot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
