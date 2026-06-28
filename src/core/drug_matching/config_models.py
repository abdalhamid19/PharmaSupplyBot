"""Configuration models for component-aware drug matching and AI review."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config_providers import PROVIDERS

ROOT_DIR = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class MatchingConfig:
    """Thresholds used by the indexed drug matcher."""

    fuzzy_threshold: int = 80
    brand_prefix_min: int = 4
    brand_prefix_ratio: float = 0.75
    fuzzy_prefix_len: int = 3
    early_stop_confidence: float = 0.95
    candidate_top_k: int = 5
    query_cache_size: int = 256
    ai_verify_threshold: float = 90.0
    ai_batch_size: int = 20
    ai_max_concurrent: int = 5
    top_k_candidates: int = 10
    ai_review_threshold: float = 0.8
    ai_search_limit: int | None = None
    ai_verify_policy: str = "score"
    ai_verify_limit: int | None = None
    ai_search_policy: str = "review-candidates"
    ai_search_min_candidate_score: float = 80.0
    ai_search_accept_confidence: float = 0.75
    ai_search_candidate_limit: int = 5
    ai_search_review_candidate_min_score: float = 68.0
    ai_search_review_candidate_limit: int = 8
    ai_search_review_accept_confidence: float = 0.85
    ai_search_allow_component_mismatch_reasons: tuple[str, ...] = (
        "different_brand",
        "brand_prefix_mismatch",
        "different_import_status",
        "different_modifier",
        "different_quantity",
        "different_volume",
    )


@dataclass(frozen=True)
class APIConfig:
    """AI API settings for verification, search, and model rotation."""

    api_key: str = ""
    api_keys: tuple[str, ...] = ()
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "openai/gpt-4o-mini"
    fallback_models: tuple[str, ...] = ()
    review_model: str = ""
    healthy_combos: tuple = ()
    attempt_plan: tuple = ()
    review_attempt_plan: tuple = ()
    max_tokens: int = 1024
    temperature: float = 0.1


@dataclass(frozen=True)
class Paths:
    """Default CSV paths for standalone product matching."""

    drugs_csv: Path = field(default_factory=lambda: ROOT_DIR / "data/input/order_items")
    tawreed_csv: Path = field(
        default_factory=lambda: ROOT_DIR / "artifacts/wardany/tawreed_products.csv"
    )
    output_csv: Path = field(default_factory=lambda: _default_output_csv())
    env_file: Path = field(default_factory=lambda: ROOT_DIR / ".env")


def _default_output_csv() -> Path:
    stem = datetime.now().strftime("matched_drugs_verified_%Y%m%d_%H%M%S.csv")
    return ROOT_DIR / "artifacts" / "matching" / stem


__all__ = [
    "ROOT_DIR",
    "MatchingConfig",
    "APIConfig",
    "Paths",
    "_default_output_csv",
]
