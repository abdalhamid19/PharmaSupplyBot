"""Configuration models for deterministic drug matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class MatchingConfig:
    """Thresholds used by the local indexed drug matcher."""

    fuzzy_threshold: int = 80
    brand_prefix_min: int = 4
    brand_prefix_ratio: float = 0.75
    fuzzy_prefix_len: int = 3
    early_stop_confidence: float = 0.95
    candidate_top_k: int = 5
    query_cache_size: int = 256
    top_k_candidates: int = 10


@dataclass(frozen=True)
class Paths:
    """Default data paths for standalone product matching."""

    drugs_csv: Path = field(default_factory=lambda: ROOT_DIR / "data/input/order_items")
    tawreed_csv: Path = field(
        default_factory=lambda: ROOT_DIR / "artifacts/wardany/tawreed_products.csv"
    )
    output_csv: Path = field(default_factory=lambda: _default_output_csv())


def _default_output_csv() -> Path:
    stem = datetime.now().strftime("matched_drugs_%Y%m%d_%H%M%S.csv")
    return ROOT_DIR / "artifacts" / "matching" / stem


__all__ = ["ROOT_DIR", "MatchingConfig", "Paths", "_default_output_csv"]
