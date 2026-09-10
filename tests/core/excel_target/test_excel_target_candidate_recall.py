"""Regression tests for review-only Excel-target candidate recall."""

from __future__ import annotations

from unittest.mock import patch

from src.core.config.config_models import MatchingConfig
from src.core.excel_target.excel_target_matching import ExcelTargetMatcher
from src.core.excel_target.excel_target_review_candidates import excel_target_row_key
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.utils.excel import Item


def _catalog() -> list[TargetProduct]:
    return [
        TargetProduct(
            code="",
            name="\u0641\u0648\u0644\u062a\u0627\u0631\u064a\u0646 3\u0645\u0628\u0648\u0644 \u0633 \u062c\u062f\u064a\u062f",
            price=51.0,
            discount_percent=0.0,
            source_file="\u0645\u062d\u0631\u0648\u06331.xlsx",
            source_row_number=3100,
        ),
        TargetProduct(
            code="",
            name="\u0641\u0648\u0644\u062a\u0627\u0631\u064a\u0646 50\u0645\u062c\u0645 - 20\u0642\u0631\u0635",
            price=48.0,
            discount_percent=0.0,
            source_file="\u0645\u062d\u0631\u0648\u06331.xlsx",
            source_row_number=3101,
        ),
        TargetProduct(
            code="",
            name="\u0641\u0648\u0644\u062a\u0627\u0631\u064a\u0646 6\u0627\u0645\u0628\u0648\u0644\u0629 \u0634\u0631\u0643\u0647",
            price=52.0,
            discount_percent=0.0,
            source_file="\u0645\u062d\u0631\u0648\u06331.xlsx",
            source_row_number=3102,
        ),
    ]


def test_review_candidates_include_the_correct_arabic_variant_without_auto_matching() -> None:
    with (
        patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={"rows": [{"en": "VOLTAREN", "ar": "فولتارين"}]},
        ),
        patch(
            "src.core.excel_target.excel_target_identity.load_dictionary",
            return_value={"by_en": {}},
        ),
        patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ),
        patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={},
        ),
    ):
        match = ExcelTargetMatcher("البركة شركات", _catalog()).match(
            Item("vol3", "VOLTAREN 3AMP", 1), MatchingConfig()
        )

    assert match.decision.best_match is None
    correct = next(
        candidate
        for candidate in match.review_candidates
        if candidate.product.source_row_number == 3100
    )
    assert correct.product.name == "فولتارين 3مبول س جديد"
    assert correct.candidate_method == "review_identity"
    assert correct.source_kind == "excel-target"
    assert correct.excel_target_source_row == 3100
    assert correct.excel_target_row_key == excel_target_row_key(
        "البركة شركات", correct.product
    )
    assert {candidate.product.source_row_number for candidate in match.review_candidates} >= {
        3100,
        3102,
    }


def test_review_candidates_include_the_correct_xithrone_pack_variant() -> None:
    catalog = [
        TargetProduct(
            code="",
            name="زيثرون 500-- 5قرص",
            price=86.0,
            discount_percent=0.0,
            source_file="محروس1.xlsx",
            source_row_number=2344,
        ),
        TargetProduct(
            code="",
            name="زيثرون 3قرص س جديد",
            price=63.0,
            discount_percent=0.0,
            source_file="محروس1.xlsx",
            source_row_number=2345,
        ),
    ]
    with (
        patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={"rows": [{"en": "XITHRONE", "ar": "زيثرون"}]},
        ),
        patch(
            "src.core.excel_target.excel_target_identity.load_dictionary",
            return_value={"by_en": {}},
        ),
        patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ),
        patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={},
        ),
    ):
        match = ExcelTargetMatcher("البركة شركات", catalog).match(
            Item("73852", "XITHRONE 500MG 3TAB", 1), MatchingConfig()
        )

    assert match.decision.best_match is None
    assert [candidate.product.source_row_number for candidate in match.review_candidates] == [2344, 2345]
