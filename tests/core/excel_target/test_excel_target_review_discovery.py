from __future__ import annotations

from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.excel_target.excel_target_aliases import AliasEntry
from src.core.excel_target.excel_target_review_discovery import (
    ExcelTargetReviewDiscoveryIndex,
    ReviewDiscoveryConfig,
)
from src.core.utils.excel import Item


def _item(name: str) -> Item:
    return Item(code="item-1", name=name, qty=1)


def test_typo_with_strong_brand_anchor_returns_review_hit() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [
            TargetProduct(
                "A",
                "AMOXICILIN PLUS 30 TABS",
                10,
                0,
                source_file="baraka.xlsx",
                source_row_number=12,
            )
        ]
    )

    hits = index.discover(
        _item("AMOXICILLIN PLU 30 TABS"),
        config=ReviewDiscoveryConfig(),
    )

    assert [hit.product.code for hit in hits] == ["A"]
    assert hits[0].strategy == "english_fuzzy"
    assert hits[0].review_status == "strong"
    assert "AMOXICILLIN" in hits[0].shared_brand_tokens
    assert hits[0].product.source_row_number == 12


def test_medium_tier_requires_a_unique_long_anchor() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [TargetProduct("A", "AMOXICILIN PLUS 30 TABS", 10, 0)]
    )

    hits = index.discover(
        _item("AMOXICILLIN PLU 30 TABS"),
        config=ReviewDiscoveryConfig(strong_score=99.0),
    )

    assert len(hits) == 1
    assert hits[0].review_status == "medium"


def test_unrelated_name_has_no_review_hit() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [TargetProduct("A", "AMOXICILIN 30 TABS", 10, 0)]
    )

    assert (
        index.discover(
            _item("PARACETAMOL 20 TABS"),
            config=ReviewDiscoveryConfig(),
        )
        == ()
    )


def test_digit_bearing_brand_tokens_do_not_cross_match() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [
            TargetProduct("b12", "VITAMIN B12 PLUS 30 CAPS", 10, 0),
            TargetProduct("b6", "VITAMIN B6 PLUS 30 CAPS", 10, 0),
        ]
    )

    hits = index.discover(_item("VITAMIN B12 PLUS 30 CAPS"), config=ReviewDiscoveryConfig())

    assert [hit.product.code for hit in hits] == ["b12"]


def test_extra_brand_prefix_does_not_create_containment_candidate() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [TargetProduct("avazir", "AVAZIR 30 TABS", 10, 0)]
    )

    assert index.discover(_item("CO AVAZIR 30 TABS"), config=ReviewDiscoveryConfig()) == ()


def test_short_shared_token_is_not_a_brand_anchor() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [TargetProduct("ab", "AB 30 TABS", 10, 0)]
    )

    assert index.discover(_item("AB 20 TABS"), config=ReviewDiscoveryConfig()) == ()


def test_same_strength_with_unrelated_brand_has_no_hit() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [TargetProduct("other", "PARACETAMOL 500 MG TABS", 10, 0)]
    )

    assert index.discover(_item("IBUPROFEN 500 MG TABS"), config=ReviewDiscoveryConfig()) == ()


def test_arabic_diacritics_and_spelling_noise_are_review_discoverable() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [
            TargetProduct(
                "ar-1",
                "بِرَايْتُوفْلِكْس 30 قرص",
                10,
                0,
                source_file="baraka.xlsx",
                source_row_number=9,
            )
        ]
    )

    hits = index.discover(
        _item("برايتوفلكس 20 قرص"),
        config=ReviewDiscoveryConfig(),
    )

    assert [hit.product.code for hit in hits] == ["ar-1"]
    assert hits[0].strategy == "arabic_fuzzy"
    assert hits[0].review_status == "variant_conflict"
    assert "pack" in hits[0].attribute_note


def test_variant_conflicts_are_retained_for_human_review() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [TargetProduct("syrup", "INODEP SYRUP 100 ML", 42, 5)]
    )

    hits = index.discover(
        _item("INODEP CAPSULES 30"),
        config=ReviewDiscoveryConfig(),
    )

    assert len(hits) == 1
    assert hits[0].review_status == "variant_conflict"
    assert "form" in hits[0].attribute_note


def test_missing_candidate_attribute_is_retained_as_unproven() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [TargetProduct("tablet", "INODEP 30", 42, 5)]
    )

    hits = index.discover(
        _item("INODEP CAPSULES 30"),
        config=ReviewDiscoveryConfig(),
    )

    assert len(hits) == 1
    assert hits[0].review_status == "variant_unproven"
    assert "form" in hits[0].attribute_note


def test_strength_and_concentration_conflicts_are_retained() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [
            TargetProduct("strength", "DANTRELAX 25 MG CAP", 10, 0),
            TargetProduct("concentration", "AUGRAM 312.5MG/60ML SYP", 10, 0),
        ]
    )

    strength_hits = index.discover(
        _item("DANTRELAX 30 MG CAP"),
        config=ReviewDiscoveryConfig(),
    )
    concentration_hits = index.discover(
        _item("AUGRAM 457MG/60ML SYP"),
        config=ReviewDiscoveryConfig(),
    )

    assert strength_hits[0].review_status == "variant_conflict"
    assert "strength" in strength_hits[0].attribute_note
    assert concentration_hits[0].review_status == "variant_conflict"
    assert "concentration" in concentration_hits[0].attribute_note


def test_equal_brand_variants_are_retained_as_ambiguous_in_stable_order() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [
            TargetProduct("b", "INODEP 30 CAPS", 10, 0, "baraka.xlsx", source_row_number=20),
            TargetProduct("a", "INODEP 30 CAPS", 10, 0, "baraka.xlsx", source_row_number=10),
        ]
    )

    hits = index.discover(_item("INODEP 30 CAPS"), config=ReviewDiscoveryConfig(limit=5))

    assert [hit.product.source_row_number for hit in hits] == [10, 20]
    assert all(hit.review_status == "ambiguous" for hit in hits)
    assert all(hit.score_margin == 0 for hit in hits)


def test_duplicate_same_row_is_deduplicated_but_distinct_rows_are_preserved() -> None:
    row = TargetProduct("same", "INODEP 30 CAPS", 10, 0, "baraka.xlsx", source_row_number=4)
    distinct_row = TargetProduct("same", "INODEP 30 CAPS", 12, 0, "baraka.xlsx", source_row_number=5)
    index = ExcelTargetReviewDiscoveryIndex.build([row, row, distinct_row])

    hits = index.discover(_item("INODEP 30 CAPS"), config=ReviewDiscoveryConfig(limit=5))

    assert [hit.product.source_row_number for hit in hits] == [4, 5]


def test_disabled_discovery_and_zero_limit_return_no_hits() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build(
        [TargetProduct("A", "AMOXICILIN 30 TABS", 10, 0)]
    )

    assert index.discover(_item("AMOXICILIN 30 TABS"), config=ReviewDiscoveryConfig(enabled=False)) == ()
    assert index.discover(_item("AMOXICILIN 30 TABS"), config=ReviewDiscoveryConfig(limit=0)) == ()


def test_cross_language_alias_is_gated_and_target_scoped() -> None:
    catalog = [
        TargetProduct(
            "generic-row",
            "\u0628\u0631\u0627\u0646\u062f \u062a\u062c\u0631\u064a\u0628\u064a 30 \u0642\u0631\u0635",
            10,
            0,
            source_file="arabic-only.xlsx",
            source_row_number=7,
        )
    ]
    index = ExcelTargetReviewDiscoveryIndex.build(
        catalog,
        review_aliases=(
            AliasEntry(
                "GENERIC BRAND",
                "\u0628\u0631\u0627\u0646\u062f \u062a\u062c\u0631\u064a\u0628\u064a",
                "fixture",
            ),
        ),
    )
    item = _item("GENERIC BRAND 30 CAPS")

    assert index.discover(item, config=ReviewDiscoveryConfig()) == ()
    hits = index.discover(
        item,
        config=ReviewDiscoveryConfig(cross_language_aliases_enabled=True),
    )

    assert len(hits) == 1
    assert hits[0].strategy == "cross_language_alias"
    assert hits[0].product.code == "generic-row"
    assert hits[0].review_status == "variant_conflict"
    assert index.discover(
        _item("UNRELATED BRAND 30 CAPS"),
        config=ReviewDiscoveryConfig(cross_language_aliases_enabled=True),
    ) == ()


def test_cross_language_alias_rejects_short_and_manufacturer_only_roots() -> None:
    catalog = [
        TargetProduct("short-row", "\u0628\u0631\0627\0646\062f \u0642\u0635\u064a\u0631 30 \u0642\u0631\u0635", 10, 0),
        TargetProduct("manufacturer-row", "\u0628\u0631\0627\0646\062f \u0634\u0631\0643\u0629 30 \u0642\u0631\u0635", 10, 0),
    ]
    index = ExcelTargetReviewDiscoveryIndex.build(
        catalog,
        review_aliases=(
            AliasEntry("AB", "\u0628\u0631\0627\0646\062f \u0642\u0635\u064a\u0631", "fixture"),
            AliasEntry("PHARMA", "\u0628\u0631\0627\0646\062f \u0634\u0631\0643\u0629", "fixture"),
        ),
    )
    config = ReviewDiscoveryConfig(cross_language_aliases_enabled=True)

    assert index.discover(_item("AB 30 CAPS"), config=config) == ()
    assert index.discover(_item("PHARMA 30 CAPS"), config=config) == ()
