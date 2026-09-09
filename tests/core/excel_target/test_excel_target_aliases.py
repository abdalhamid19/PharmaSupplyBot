import pytest

from src.core.excel_target.excel_target_aliases import (
    AliasCandidate,
    AliasEntry,
    ExcelTargetAliasResolver,
)
from src.core.excel_target.excel_target_loader import TargetProduct


def test_resolves_a_high_confidence_typo_to_a_real_target_product() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {
                "en": "AMOXICILLINCLAV",
                "ar": "اموكسيسيلين كلاف",
                "source": "tawreed",
            }
        ],
        target_products=[
            TargetProduct(
                code="target-1",
                name="اموكسيسيلين كلاف 625 مجم 14 قرص",
                price=10.0,
                discount_percent=0.0,
            )
        ],
    )

    candidates = resolver.resolve("AMOXICILLINCLAVV 625MG 14TAB")

    assert candidates == (
        AliasCandidate(
            product_id="target-1",
            canonical_brand="AMOXICILLINCLAV",
            source="tawreed",
            score=pytest.approx(96.7, abs=0.2),
            runner_up_margin=pytest.approx(100.0),
        ),
    )


def test_meaningful_men_women_modifier_blocks_a_collision() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {"en": "CENTRUM WOMEN", "ar": "سنترم وومن", "source": "egyptian"},
            {"en": "CENTRUM MEN", "ar": "سنترم رجال", "source": "egyptian"},
        ],
        target_products=[
            TargetProduct("women", "سنترم وومن 30 قرص", 10.0, 0.0),
            TargetProduct("men", "سنترم رجال 30 قرص", 10.0, 0.0),
        ],
    )

    assert resolver.resolve("CENTRUM MEN 30 TAB") == (
        AliasCandidate(
            product_id="men",
            canonical_brand="CENTRUM MEN",
            source="egyptian",
            score=100.0,
            runner_up_margin=100.0,
        ),
    )


def test_digit_bearing_and_meaningful_plus_tokens_are_not_dropped() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {"en": "VITAMIN B12 PLUS", "ar": "فيتامين بي 12 بلس", "source": "tawreed"},
            {"en": "VITAMIN B6 PLUS", "ar": "فيتامين بي 6 بلس", "source": "tawreed"},
        ],
        target_products=[
            TargetProduct("b12", "فيتامين بي 12 بلس 30 كبسول", 10.0, 0.0),
            TargetProduct("b6", "فيتامين بي 6 بلس 30 كبسول", 10.0, 0.0),
        ],
    )

    candidates = resolver.resolve("VITAMIN B12 PLUS 30 CAPS")

    assert [candidate.product_id for candidate in candidates] == ["b12"]


def test_a_safe_spaced_b12_variant_keeps_the_same_digit_bearing_token() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {"en": "VITAMIN B12", "ar": "فيتامين بي 12", "source": "egyptian"}
        ],
        target_products=[TargetProduct("b12", "فيتامين بي 12 30 كبسول", 10.0, 0.0)],
    )

    assert [candidate.product_id for candidate in resolver.resolve("VITAMIN B 12 30 CAPS")] == [
        "b12"
    ]


def test_typo_below_the_hard_floor_is_not_alias_evidence() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {"en": "BRAYTOFLEX", "ar": "برايتوفلكس", "source": "tawreed"}
        ],
        target_products=[TargetProduct("target-1", "برايتوفلكس 30 قرص", 10.0, 0.0)],
    )

    assert resolver.resolve("BRAYTOFLEXX 30 TAB") == ()


def test_equal_or_near_equal_aliases_fail_the_runner_up_margin_gate() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {
                "en": "AMOXICILLINCLAV",
                "ar": "اموكسيسيلين كلاف ا",
                "source": "tawreed",
            },
            {
                "en": "AMOXICILLINCLAVV",
                "ar": "اموكسيسيلين كلاف ب",
                "source": "egyptian",
            },
        ],
        target_products=[
            TargetProduct("a", "اموكسيسيلين كلاف ا 625 مجم 14 قرص", 10.0, 0.0),
            TargetProduct("b", "اموكسيسيلين كلاف ب 625 مجم 14 قرص", 10.0, 0.0),
        ],
    )

    assert resolver.resolve("AMOXICILLINCLAV 625MG 14TAB") == ()


def test_one_strong_alias_can_return_multiple_target_variants_for_caller_filtering() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {"en": "INODEP", "ar": "اينوديب", "source": "egyptian"}
        ],
        target_products=[
            TargetProduct("syrup", "اينوديب شراب 100 مل", 10.0, 0.0),
            TargetProduct("capsule", "اينوديب 30 كبسول", 10.0, 0.0),
        ],
    )

    candidates = resolver.resolve("INODEP 30 CAPS")

    assert {candidate.product_id for candidate in candidates} == {"syrup", "capsule"}
    assert all(candidate.score == 100.0 for candidate in candidates)
    assert all(candidate.runner_up_margin == 100.0 for candidate in candidates)


@pytest.mark.parametrize(
    "modifier",
    ["PLUS", "DUO", "TRIO", "MEN", "WOMEN", "FORTE", "NIGHT", "XR"],
)
def test_each_meaningful_modifier_is_preserved_exactly(modifier: str) -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {"en": f"LONGBRAND {modifier}", "ar": f"براند {modifier}", "source": "tawreed"}
        ],
        target_products=[
            TargetProduct("target-1", f"براند {modifier} 30 قرص", 10.0, 0.0)
        ],
    )

    assert resolver.resolve(f"LONGBRAND {modifier} 30 TAB")
    different_modifier = "MEN" if modifier != "MEN" else "WOMEN"
    assert resolver.resolve(f"LONGBRAND {different_modifier} 30 TAB") == ()


def test_local_dictionary_shape_and_alias_entry_are_supported() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries={
            "by_en": {
                "INODEP": [
                    {"ar": "اينوديب", "source": "egyptian"},
                ]
            }
        },
        target_products=[TargetProduct("inodep", "اينوديب 30 كبسول", 10.0, 0.0)],
    )
    explicit = ExcelTargetAliasResolver(
        alias_entries=[AliasEntry("INODEP", "اينوديب", "egyptian")],
        target_products=[TargetProduct("inodep", "اينوديب 30 كبسول", 10.0, 0.0)],
    )

    assert resolver.resolve("INODEP 30 CAPS")[0].source == "egyptian"
    assert explicit.resolve("INODEP 30 CAPS")[0].product_id == "inodep"


def test_alias_without_a_real_target_row_cannot_create_a_candidate() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {"en": "INODEP", "ar": "اينوديب", "source": "tawreed"}
        ],
        target_products=[TargetProduct("other", "سالبوفنت 30 قرص", 10.0, 0.0)],
    )

    assert resolver.resolve("INODEP 30 CAPS") == ()


def test_score_floor_and_margin_floor_cannot_be_relaxed() -> None:
    with pytest.raises(ValueError, match="hard floor of 96"):
        ExcelTargetAliasResolver([], [], min_score=95)
    with pytest.raises(ValueError, match="lower than 4"):
        ExcelTargetAliasResolver([], [], min_runner_up_margin=3)


def test_duplicate_source_evidence_for_one_product_keeps_tawreed_provenance() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {"en": "INODEP", "ar": "اينوديب", "source": "egyptian"},
            {"en": "INODEP", "ar": "اينوديب", "source": "tawreed"},
        ],
        target_products=[TargetProduct("inodep", "اينوديب 30 كبسول", 10.0, 0.0)],
    )

    candidates = resolver.resolve("INODEP 30 CAPS")

    assert len(candidates) == 1
    assert candidates[0].product_id == "inodep"
    assert candidates[0].source == "tawreed"
