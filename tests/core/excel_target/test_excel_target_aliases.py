import pytest

from src.core.excel_target.excel_target_aliases import (
    AliasCandidate,
    AliasEntry,
    ExcelTargetAliasResolver,
)
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.excel_target.excel_target_identity import ExcelTargetBilingualIndex


def test_configured_alias_is_scoped_to_the_target_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
        lambda: {"rows": ()},
    )
    monkeypatch.setattr(
        "src.core.excel_target.excel_target_identity.load_dictionary",
        lambda: {"by_en": {}},
    )
    monkeypatch.setattr(
        "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
        lambda names: {},
    )
    alias = {
        "en": "LEVOFLOXACIN-EVA",
        "ar": "ليفوفلوكساسين ايفا 500مجم 10اقراص",
        "source": "baraka-1209",
    }
    product = TargetProduct("levo", "ليفوفلوكساسين ايفا 500مجم 10اقراص", 10.0, 0.0)

    scoped = ExcelTargetBilingualIndex.build(
        [product], allow_live_translation=False, alias_entries=[alias]
    )
    identified = scoped.identify("LEVOFLOXACIN-EVA 500 MG 10 F.C.TABS.")
    assert [entry.product.code for entry in identified] == ["levo"]
    assert identified[0].evidence.kind == "safe_alias"

    other = ExcelTargetBilingualIndex.build(
        [TargetProduct("other", "سالبوتامول شراب", 10.0, 0.0)],
        allow_live_translation=False,
        alias_entries=[alias],
    )
    assert other.identify("LEVOFLOXACIN-EVA 500 MG 10 F.C.TABS.") == ()


def test_dotted_iu_and_film_coated_tablet_tokens_are_ignored_for_alias_brand() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {"en": "PENCITARD", "ar": "بنسيتارد فيال", "source": "baraka-1209"},
            {
                "en": "LEVOFLOXACIN-EVA",
                "ar": "ليفوفلوكساسين ايفا 500مجم 10اقراص",
                "source": "baraka-1209",
            },
        ],
        target_products=[
            TargetProduct("pen", "بنسيتارد فيال", 10.0, 0.0),
            TargetProduct("levo", "ليفوفلوكساسين ايفا 500مجم 10اقراص", 10.0, 0.0),
        ],
    )

    assert resolver.resolve("PENCITARD 1200000 i.u vial")[0].product_id == "pen"
    assert resolver.resolve("LEVOFLOXACIN-EVA 500 MG 10 F.C.TABS.")[0].product_id == "levo"


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


def test_p001_cogicine_uses_the_reviewed_tawreed_spelling_variant() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {
                "en": "COGICIN 30 TABS",
                "ar": "كوجيسين 30 اقراص",
                "source": "tawreed",
            }
        ],
        target_products=[
            TargetProduct("cogicin", "كوجيسين 30 قرص", 95.0, 0.0),
        ],
    )

    candidates = resolver.resolve("COGICINE 30 TABS")

    assert candidates == (
        AliasCandidate(
            product_id="cogicin",
            canonical_brand="COGICINE",
            source="tawreed",
            score=100.0,
            runner_up_margin=100.0,
        ),
    )


def test_p007_explicit_bilingual_alias_is_scoped_to_the_confirmed_target_name() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {
                "en": "HERO BABY LF",
                "ar": "هيرو بابي لف ميلك",
                "source": "egyptian",
            }
        ],
        target_products=[
            TargetProduct("lf", "لبن هيرو بيبى ال اف 400 جم", 399.0, 0.0),
            TargetProduct("ha", "هيرو بيبي اتش ايه لبن 400 جم", 419.0, 0.0),
        ],
    )

    candidates = resolver.resolve("HERO BABY LF MILK")

    assert candidates == (
        AliasCandidate(
            product_id="lf",
            canonical_brand="HERO BABY LF MILK",
            source="egyptian",
            score=100.0,
            runner_up_margin=100.0,
        ),
    )


def test_existing_custom_alias_sources_remain_supported() -> None:
    resolver = ExcelTargetAliasResolver(
        alias_entries=[
            {
                "en": "UNAPPROVED BRAND",
                "ar": "براند غير معتمد",
                "source": "manual_review_note",
            }
        ],
        target_products=[
            TargetProduct("unapproved", "براند غير معتمد 30 قرص", 10.0, 0.0),
        ],
    )

    assert resolver.resolve("UNAPPROVED BRAND 30 TABS") == (
        AliasCandidate(
            product_id="unapproved",
            canonical_brand="UNAPPROVED BRAND",
            source="manual_review_note",
            score=100.0,
            runner_up_margin=100.0,
        ),
    )
