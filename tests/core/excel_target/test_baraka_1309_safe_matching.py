"""Regression coverage for the independent Baraka 1309 target."""

from __future__ import annotations

from pathlib import Path

from src.core.config.config import load_config
from src.core.config.config_models import MatchingConfig
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.excel_target.excel_target_matching import ExcelTargetMatcher
from src.core.utils.excel import Item


def _catalog() -> list[TargetProduct]:
    rows = {
        164: "اربيبرازول15 مجم اقراص",
        983: "بالينا اوميجا 3 جاميز برطمان علبه + علبه عرض",
        1123: "بريجناستيب1 اقراص",
        1211: "بنسيتارد فيال",
        2281: "زولاديكس 3.6مجم 1سرنجة",
        2769: "سينوبار اس صابونة",
        3399: "كوادريدرم كريم س ج",
        3986: "ميبو سى كريم",
        4035: "ميلا كريست 1.5مجم  لزقه20 فيلم",
        4075: "مينوبيس اورجينال 30 قرص",
    }
    return [
        TargetProduct(
            code="",
            name=name,
            price=10.0,
            discount_percent=0.0,
            source_file="البركة1309.xlsx",
            source_row_number=row,
        )
        for row, name in rows.items()
    ]


def test_baraka_1309_target_is_configured_with_its_own_sheet_and_alias_scope() -> None:
    config = load_config(Path("state/config.yaml"))
    target = config.excel_targets["البركة1309"]

    assert target.sheet == "محروس"
    assert target.name_col == "الصنف"
    assert target.discount_col == "شركات"
    assert len(target.aliases) == 9
    assert len(target.review_aliases) == 1
    assert all("البركة1309.xlsx row " in alias["source"] for alias in target.aliases)


def test_baraka_1309_items_are_matched_or_reviewed_without_unsafe_substitutions() -> None:
    config = load_config(Path("state/config.yaml"))
    target = config.excel_targets["البركة1309"]
    matcher = ExcelTargetMatcher(
        "البركة1309",
        _catalog(),
        allow_live_translation=False,
        use_saved_approvals=False,
        approved_aliases=target.aliases,
        review_identity_aliases=target.review_aliases,
    )
    expected = {
        "ARIPIPRAZOLE 15 MG 20 TAB": "review",
        "BALENA OMEGA GUMMIES (1 FREE) 30 GUMMIES": "review",
        "LIMITLESS MILGA MAX 30 TABS": "no_match",
        "MEBO OINT 30 GM": "review",
        "MELACRYST 1.5 MG 20 FILMS": "auto_match",
        "MENOPACE 30 TAB": "review",
        "OMEGALOX-3 1000 MG 30 CAPS.": "no_match",
        "PENCITARD 1200000 i.u vial": "review",
        "PREGNASTEP 1 PRENATAL 30 F.C. TABS": "review",
        "SYNOBAR-S SOAP 100GM": "review",
        "ZOLADEX DEPOT 3.6 MG AM": "review",
        "quadriderm cream 15g": "review",
    }

    for index, (name, wanted) in enumerate(expected.items(), start=1):
        result = matcher.match(Item(str(index), name, 1), MatchingConfig())
        if result.decision.best_match is not None:
            actual = "auto_match"
        elif result.review_candidates:
            actual = "review"
        else:
            actual = "no_match"
        assert actual == wanted, (name, actual, result.decision.final_reason)

    limitless = matcher.match(
        Item("92558", "LIMITLESS MILGA MAX 30 TABS", 1), MatchingConfig()
    )
    assert limitless.decision.best_match is None
    assert not any(
        "MAN MAX" in candidate.product_name for candidate in limitless.review_candidates
    )
