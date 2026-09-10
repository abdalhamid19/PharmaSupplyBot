"""Regression tests for review-only Excel-target candidate recall."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from src.core.config.config_models import MatchingConfig
from src.core.excel_target.excel_target_identity import (
    IdentifiedTarget,
    IdentityEvidence,
)
from src.core.excel_target.excel_target_aliases import AliasEntry
from src.core.excel_target.excel_target_matching import (
    ExcelTargetMatcher,
    _compatible_identified,
    _identity_decision,
)
from src.core.excel_target.excel_target_review_candidates import excel_target_row_key
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.utils.excel import Item


def test_review_only_identity_is_rejected_by_automatic_compatibility_gate() -> None:
    product = TargetProduct(
        code="",
        name="\u0641\u0648\u0644\u062a\u0627\u0631\u064a\u0646 3\u0645\u0628\u0648\u0644 \u0633 \u062c\u062f\u064a\u062f",
        price=51.0,
        discount_percent=0.0,
        source_file="\u0645\u062d\u0631\u0648\u06331.xlsx",
        source_row_number=3100,
    )
    identified = IdentifiedTarget(
        product,
        IdentityEvidence(
            "review_identity",
            "VOLTAREN",
            "review-only anchored Arabic brand expansion",
            0.90,
        ),
    )

    accepted, rejected = _compatible_identified(
        Item("vol3", "VOLTAREN 3AMP", 1),
        (identified,),
    )

    assert accepted == []
    assert rejected == ["review_identity evidence requires manual review"]
    with pytest.raises(ValueError, match="review_identity"):
        _identity_decision(Item("vol3", "VOLTAREN 3AMP", 1), identified, 0.0)


@pytest.mark.parametrize("evidence_kind", ["unknown_future", "discovery_only"])
def test_unknown_identity_evidence_fails_closed_for_automatic_matching(
    evidence_kind: str,
) -> None:
    product = TargetProduct(
        "",
        "\u0641\u0648\u0644\u062a\u0627\u0631\u064a\u0646 3\u0645\u0628\u0648\u0644",
        51.0,
        0.0,
    )
    identified = IdentifiedTarget(
        product,
        IdentityEvidence(evidence_kind, "VOLTAREN", "future evidence", 1.0),
    )

    accepted, rejected = _compatible_identified(
        Item("vol3", "VOLTAREN 3AMP", 1), (identified,)
    )

    assert accepted == []
    assert rejected == [f"{evidence_kind} evidence requires manual review"]
    with pytest.raises(ValueError, match=evidence_kind):
        _identity_decision(Item("vol3", "VOLTAREN 3AMP", 1), identified, 0.0)


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
    prefixed = next(
        candidate
        for candidate in match.review_candidates
        if candidate.product.source_row_number == 3102
    )
    assert prefixed.candidate_method == "review_identity_prefix"


def test_review_alias_anchor_works_without_a_bare_arabic_target_row() -> None:
    catalog = [
        TargetProduct(
            code="",
            name="\u0641\u0648\u0644\u062a\u0627\u0631\u064a\u0646 3\u0645\u0628\u0648\u0644 \u0633 \u062c\u062f\u064a\u062f",
            price=51.0,
            discount_percent=0.0,
            source_file="\u0645\u062d\u0631\u0648\u06331.xlsx",
            source_row_number=3100,
        )
    ]
    with (
        patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={"rows": [{"en": "VOLTAREN", "ar": "\u0641\u0648\u0644\u062a\u0627\u0631\u064a\u0646"}]},
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
        match = ExcelTargetMatcher("baraka", catalog).match(
            Item("vol3", "VOLTAREN 3AMP", 1), MatchingConfig()
        )

    assert match.decision.best_match is None
    assert [candidate.product.source_row_number for candidate in match.review_candidates] == [
        3100
    ]
    assert match.review_candidates[0].candidate_method == "review_identity"


def test_cross_language_review_alias_never_becomes_automatic_match() -> None:
    arabic_brand = "".join(
        chr(codepoint)
        for codepoint in (
            0x628,
            0x631,
            0x627,
            0x646,
            0x62F,
            0x20,
            0x62A,
            0x62C,
            0x631,
            0x64A,
            0x628,
            0x64A,
        )
    )
    arabic_pack = "".join(chr(codepoint) for codepoint in (0x642, 0x631, 0x635))
    catalog = [
        TargetProduct(
            "generic-row",
            f"{arabic_brand} 30 {arabic_pack}",
            51.0,
            0.0,
            source_file="arabic-only.xlsx",
            source_row_number=7,
        )
    ]
    matcher = ExcelTargetMatcher(
        "baraka",
        catalog,
        review_aliases=(
            AliasEntry(
                "GENERIC BRAND",
                "\u0628\u0631\u0627\0646\u062f \u062a\062c\0631\u064a\u0628\u064a",
                "fixture",
            ),
            AliasEntry("GENERIC BRAND", arabic_brand, "fixture-correct"),
        ),
    )

    match = matcher.match(
        Item("generic", "GENERIC BRAND 30 CAPS", 1),
        MatchingConfig(excel_target_review_cross_language_aliases_enabled=True),
    )

    assert match.decision.best_match is None
    assert len(match.review_candidates) == 1
    assert match.review_candidates[0].candidate_method == "cross_language_alias"


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
