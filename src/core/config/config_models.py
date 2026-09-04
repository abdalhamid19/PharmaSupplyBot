"""Configuration dataclasses used by the Tawreed bot."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.errors import ValidationError

@dataclass(frozen=True)
class ExcelConfig:
    """Excel column names and quantity bounds used to load shortage items."""

    code_col: str
    name_col: str
    qty_col: str
    min_qty: int = 1
    max_qty: int = 10**9


@dataclass(frozen=True)
class ExcelTargetConfig:
    """Excel catalog columns used as a secondary match source.

    The Excel target source behaves like a Tawreed profile: each configured
    target is a pharmacy/vendor catalog (``name`` + ``price`` + ``discount``)
    that the matching engine searches in addition to the live Tawreed
    profiles. The matching algorithm is identical; only the search surface
    changes (in-memory catalog scan instead of HTTP/API/Playwright).

    ``price_meaning`` declares what the single ``price_col`` represents in
    this catalog. The default ``"public_with_discount"`` treats the column
    as the retail price (what the end customer pays) and derives the
    pharmacy purchase price from ``public × (1 − discount)``.
    ``"purchase_only"`` treats the column as already-discounted and
    mirrors it into both price fields. ``"public_only"`` leaves the
    purchase side ``NULL``.
    """

    name_col: str
    price_col: str
    discount_col: str
    display_name: str = ""
    code_col: str = ""
    sheet: str = ""
    header_row: int = 0
    enabled: bool = True
    price_meaning: str = "public_with_discount"

    @property
    def requires_code(self) -> bool:
        """Return whether the catalog needs an explicit code column."""
        return bool(self.code_col)


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
    submit_order: bool = False
    max_workers: int = 1
    item_workers: int = 1

@dataclass(frozen=True)
class MatchingConfig:
    """Thresholds that decide whether a Tawreed product match is acceptable."""

    exact_match_accept: bool = True
    high_overlap_threshold: float = 0.85
    medium_score_threshold: float = 12.0
    medium_overlap_threshold: float = 0.6
    numeric_score_threshold: float = 20.0
    numeric_overlap_threshold: float = 0.45
    numeric_score_weight: float = 4.0
    critical_token_penalty: float = 2.0
    distinguishing_token_penalty: float = 3.0
    semantic_mismatch_penalty: float = 10.0
    early_stop_confidence: float = 0.95
    candidate_top_k: int = 5
    fuzzy_prefix_len: int = 3
    query_cache_size: int = 256
    manual_review_save_candidate_limit: int = 5
    manual_review_display_candidate_limit: int = 5
    require_identity_token_for_flag: bool = True
    enable_auto_save_verified_match: bool = True
    enable_auto_match_re_review_on_fail: bool = False
    enable_approved_match_re_review_on_fail: bool = False
    enable_manufacturer_check: bool = False
    manufacturer_match_threshold: float = 0.85
    reject_extra_brand_token: bool = False

@dataclass(frozen=True)
class DatabaseConfig:
    """Local SQLite persistence settings for order-run analytics."""

    order_runs_enabled: bool = True
    order_runs_path: str = ""
    store_candidates: bool = False

    def persistence_options(self) -> dict[str, Any]:
        """Return the options dict consumed by order-run persistence.

        ``path`` is omitted when unset so the persistence layer falls through to
        its own default resolution instead of treating "" as an off switch.
        """
        options: dict[str, Any] = {"enabled": self.order_runs_enabled}
        if self.order_runs_path:
            options["path"] = self.order_runs_path
        return options

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
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    excel_targets: dict[str, ExcelTargetConfig] = field(default_factory=dict)

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
        raise ValidationError(
            "Please provide --profile <name> or use --all-profiles",
            hint="Re-run the command with one of these flags.",
        )

    def _selected_profile(self, profile: str) -> list[tuple[str, ProfileConfig]]:
        """Return one explicitly selected profile or raise a descriptive error."""
        if profile not in self.profiles:
            available_profiles = ", ".join(self.profiles.keys())
            raise ValidationError(
                f"Unknown profile '{profile}'. Available: {available_profiles}",
                            hint="Re-run with one of the available profile names.",
            )
        return [(profile, self.profiles[profile])]

    def enabled_excel_targets(self) -> dict[str, ExcelTargetConfig]:
        """Return every configured Excel target that is enabled."""
        return {
            key: cfg for key, cfg in self.excel_targets.items() if cfg.enabled
        }

    def excel_targets_to_run(
        self,
        excel_target: str | None,
        all_excel_targets: bool,
    ) -> list[tuple[str, ExcelTargetConfig]]:
        """Return the configured excel targets requested by the CLI arguments."""
        enabled = self.enabled_excel_targets()
        if all_excel_targets:
            return list(enabled.items())
        if excel_target:
            if excel_target not in enabled:
                available = ", ".join(enabled.keys()) or "<none>"
                raise ValidationError(
                    f"Unknown excel-target '{excel_target}'. Available: {available}",
                    hint="Re-run with one of the available excel-target names.",
                )
            return [(excel_target, enabled[excel_target])]
        return []
