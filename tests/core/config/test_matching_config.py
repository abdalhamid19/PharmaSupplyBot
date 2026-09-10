from __future__ import annotations

from pathlib import Path

from src.core.config.config import load_config
from src.core.config.config_models import MatchingConfig


def test_excel_review_discovery_defaults_are_conservative() -> None:
    config = MatchingConfig()

    assert config.excel_target_review_candidates_enabled is True
    assert config.excel_target_review_cross_language_aliases_enabled is False
    assert config.excel_target_review_candidate_limit == 5
    assert config.excel_target_review_fuzzy_strong_score == 90.0
    assert config.excel_target_review_fuzzy_strong_margin == 8.0
    assert config.excel_target_review_fuzzy_medium_score == 86.0
    assert config.excel_target_review_fuzzy_medium_margin == 12.0
    assert config.excel_target_review_ambiguous_score == 88.0
    assert config.excel_target_review_ambiguous_margin == 8.0


def test_state_config_exposes_the_same_review_discovery_policy() -> None:
    config = load_config(Path("state/config.yaml"))

    assert config.matching.excel_target_review_candidates_enabled is True
    assert config.matching.excel_target_review_candidate_limit == 5
    assert config.matching.excel_target_review_fuzzy_strong_score == 90.0
    assert config.matching.excel_target_review_fuzzy_strong_margin == 8.0
    assert config.matching.excel_target_review_fuzzy_medium_score == 86.0
    assert config.matching.excel_target_review_fuzzy_medium_margin == 12.0
    assert config.matching.excel_target_review_ambiguous_score == 88.0
    assert config.matching.excel_target_review_ambiguous_margin == 8.0
