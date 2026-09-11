"""Contracts for strict medicine-variant compatibility."""

import pytest

from src.core.excel_target.product_attributes import validate_product_compatibility
from src.core.excel_target.product_attributes import extract_product_attributes


def test_gram_and_milligram_strengths_are_equivalent() -> None:
    result = validate_product_compatibility("PRODUCT 1 G CREAM", "منتج 1000 مجم كريم")
    assert result.accepted


def test_volume_never_matches_mass() -> None:
    result = validate_product_compatibility("PRODUCT 100 MG SYRUP", "منتج 100 مل شراب")
    assert not result.accepted
    assert "strength" in result.rejection_reason


def test_missing_explicit_strength_requires_review() -> None:
    result = validate_product_compatibility("PRODUCT 100 MG CAPSULES 30", "منتج 30 كبسول")
    assert not result.accepted
    assert result.rejection_reason == "candidate strength is not proven"


def test_conflicting_pack_is_rejected() -> None:
    result = validate_product_compatibility("PRODUCT CAPSULES 30", "منتج 20 كبسول")
    assert not result.accepted
    assert result.rejection_reason == "candidate pack conflicts with requested pack"


def test_mgc_typo_is_normalized_to_mcg_without_matching_mg() -> None:
    result = validate_product_compatibility(
        "PRODUCT 1000 MGC CAPSULES", "منتج 1000 ميكروجرام كبسول"
    )
    assert result.accepted

    mismatch = validate_product_compatibility(
        "PRODUCT 1000 MGC CAPSULES", "منتج 1000 مجم كبسول"
    )
    assert not mismatch.accepted
    assert "strength" in mismatch.rejection_reason


def test_flim_and_film_are_the_same_explicit_form() -> None:
    result = validate_product_compatibility("PRODUCT 20 FLIM", "منتج 20 FILM")
    assert result.accepted


def test_film_does_not_match_tablet() -> None:
    result = validate_product_compatibility("PRODUCT 20 FLIM", "منتج 20 TABLETS")
    assert not result.accepted
    assert result.rejection_reason == "candidate form conflicts with requested form"


def test_arabic_singular_and_plural_forms_are_equivalent() -> None:
    result = validate_product_compatibility("PRODUCT CAPSULES 30", "منتج 30 كبسوله")
    assert result.accepted


def test_arabic_nokot_is_an_explicit_drops_form() -> None:
    result = validate_product_compatibility("PRODUCT DROPS 15 ML", "منتج نقط 15 مل")
    assert result.accepted


def test_bare_drops_dose_distinguishes_750_from_1000() -> None:
    correct = validate_product_compatibility(
        "LACTASE 750 DROPS 15 ML",
        "لاكتيز 750 نقط 15 مل",
    )
    wrong = validate_product_compatibility(
        "LACTASE 750 DROPS 15 ML",
        "لاكتيز 1000 نقط 15 مل",
    )

    assert correct.accepted
    assert not wrong.accepted
    assert "strength" in wrong.rejection_reason


@pytest.mark.parametrize(
    ("candidate", "accepted"),
    [
        ("LACTASE 1000 ORAL DROPS 15 ML", True),
        ("LACTASE 750 ORAL DROPS 15 ML", False),
        ("\u0644\u0627\u0643\u062a\u064a\u0632 1000 \u0646\u0642\u0637 15 \u0645\u0644", True),
        ("\u0644\u0627\u0643\u062a\u064a\u0632 750 \u0646\u0642\u0637 15 \u0645\u0644", False),
        ("\u0644\u0627\u0643\u062a\u064a\u0632 1000 \u0642\u0637\u0631\u0647 15 \u0645\u0644", True),
        ("\u0644\u0627\u0643\u062a\u064a\u0632 750 \u0642\u0637\u0631\u0647 15 \u0645\u0644", False),
        ("\u0644\u0627\u0643\u062a\u064a\u0632 1000 \u0645\u062c\u0645 \u0642\u0637\u0631\u0647 \u0628\u0627\u0644\u0641\u0645 15 \u0645\u0644", True),
        ("\u0644\u0627\u0643\u062a\u064a\u0632 750 \u0645\u062c\u0645 \u0642\u0637\u0631\u0647 \u0628\u0627\u0644\u0641\u0645 15 \u0645\u0644", False),
    ],
)
def test_lactase_oral_drops_strength_is_pinned_across_languages(
    candidate: str, accepted: bool
) -> None:
    result = validate_product_compatibility(
        "LACTASE 1000 ORAL DROPS 15 ML", candidate
    )

    assert result.accepted is accepted
    if not accepted:
        assert "strength" in result.rejection_reason


def test_supplier_sharab_does_not_prove_suspension_presentation() -> None:
    result = validate_product_compatibility(
        "PRODUCT 457 MG SUSP 60 ML",
        "منتج 457 مجم شراب 60 مل",
    )
    assert not result.accepted
    assert result.rejection_reason == "candidate form conflicts with requested form"


def test_arabic_film_pack_count_is_checked() -> None:
    result = validate_product_compatibility("PRODUCT FILM 20", "منتج 10 فيلم")
    assert not result.accepted
    assert result.rejection_reason == "candidate pack conflicts with requested pack"


def test_ointment_does_not_match_cream() -> None:
    result = validate_product_compatibility(
        "PRODUCT 0.1% OINT 15 G", "منتج 0.1% كريم 15 جم"
    )
    assert not result.accepted
    assert result.rejection_reason == "candidate form conflicts with requested form"


def test_unrequested_candidate_strength_stays_manual_review() -> None:
    result = validate_product_compatibility(
        "PRODUCT SPRAY", "منتج 150 مجم سبراى"
    )
    assert not result.accepted
    assert result.rejection_reason == "candidate has an unrequested strength"


def test_reordered_compound_strengths_preserve_their_components() -> None:
    result = validate_product_compatibility(
        "PRODUCT 228/5 MG SUSP",
        "منتج 5/228 مجم معلق",
    )

    assert result.accepted
    assert len(result.query.concentrations) == 1
    concentration = next(iter(result.query.concentrations))
    assert concentration.denominator == ()
    assert {(part.value, part.unit) for part in concentration.numerator} == {
        (228.0, "mg"),
        (5.0, "mg"),
    }
    assert result.query.concentrations == result.candidate.concentrations


def test_ratio_concentration_preserves_direction_and_rejects_wrong_dilution() -> None:
    result = validate_product_compatibility(
        "PRODUCT 250MG/5ML SOLUTION",
        "منتج 250 مجم / 5 مل محلول",
    )
    assert result.accepted
    concentration = next(iter(result.query.concentrations))
    assert len(concentration.numerator) == 1
    assert len(concentration.denominator) == 1
    assert concentration.numerator[0].value == 250.0
    assert concentration.numerator[0].unit == "mg"
    assert concentration.denominator[0].value == 5.0
    assert concentration.denominator[0].unit == "ml"

    reversed_ratio = validate_product_compatibility(
        "PRODUCT 250MG/5ML SOLUTION",
        "منتج 5 مل / 250 مجم محلول",
    )
    assert not reversed_ratio.accepted
    assert "concentration" in reversed_ratio.rejection_reason

    wrong_dilution = validate_product_compatibility(
        "PRODUCT 250MG/5ML SOLUTION",
        "منتج 250 مجم / 10 مل محلول",
    )
    assert not wrong_dilution.accepted
    assert "concentration" in wrong_dilution.rejection_reason


def test_two_explicit_same_unit_ratio_preserves_direction() -> None:
    reversed_ratio = validate_product_compatibility(
        "PRODUCT 1MG/100MG SOLUTION",
        "منتج 100 مجم/1 مجم محلول",
    )

    assert not reversed_ratio.accepted
    assert "concentration" in reversed_ratio.rejection_reason

    missing_ratio = validate_product_compatibility(
        "PRODUCT 250MG/5ML SOLUTION",
        "منتج 250 مجم محلول",
    )
    assert not missing_ratio.accepted
    assert missing_ratio.rejection_reason == "candidate concentration is not proven"


def test_compound_strength_requires_all_components_but_not_their_order() -> None:
    result = validate_product_compatibility(
        "PRODUCT 5/12.5/40 MG POWDER",
        "منتج 40/5/12.5 مجم بودرة",
    )
    assert result.accepted

    missing_component = validate_product_compatibility(
        "PRODUCT 5/12.5/40 MG POWDER",
        "منتج 40/5/20 مجم بودرة",
    )
    assert not missing_component.accepted
    assert "concentration" in missing_component.rejection_reason


def test_backslash_compound_separator_is_equivalent_to_slash() -> None:
    result = validate_product_compatibility(
        "PRODUCT 10/160 MG 28 TAB",
        r"منتج 10\160 مجم 28 قرص",
    )
    assert result.accepted


def test_arabic_units_and_decimal_values_are_canonicalized() -> None:
    result = validate_product_compatibility(
        "PRODUCT 250MG/5ML SOLUTION",
        "منتج 250 مجم/٥ مل محلول",
    )
    assert result.accepted

    decimal_result = validate_product_compatibility(
        "PRODUCT 12.5 MG",
        "منتج ١٢٫٥ مجم",
    )
    assert decimal_result.accepted
    assert decimal_result.query.strengths == decimal_result.candidate.strengths


@pytest.mark.parametrize(
    ("english_form", "arabic_form"),
    [
        ("SUSP", "معلق"),
        ("SOLUTION", "محلول"),
        ("LOTION", "لوشن"),
        ("VIAL", "فيال"),
        ("AMPOULE", "امبول"),
        ("SUPPOSITORY", "لبوس"),
        ("LOZENGE", "استحلاب"),
        ("POWDER", "بودرة"),
    ],
)
def test_distinct_form_vocabulary_matches_arabic_aliases(
    english_form: str, arabic_form: str
) -> None:
    result = validate_product_compatibility(
        f"PRODUCT {english_form}",
        f"منتج {arabic_form}",
    )
    assert result.accepted


@pytest.mark.parametrize(
    ("query_form", "candidate_form"),
    [
        ("SUSP", "محلول"),
        ("SOLUTION", "لوشن"),
        ("VIAL", "امبول"),
        ("SUPPOSITORY", "استحلاب"),
        ("LOZENGE", "بودرة"),
    ],
)
def test_distinct_forms_reject_conflicting_presentations(
    query_form: str, candidate_form: str
) -> None:
    result = validate_product_compatibility(
        f"PRODUCT {query_form}",
        f"منتج {candidate_form}",
    )
    assert not result.accepted
    assert result.rejection_reason == "candidate form conflicts with requested form"


def test_ampoule_and_vial_are_distinct_counted_presentations() -> None:
    result = validate_product_compatibility(
        "PRODUCT 2 AMPOULES",
        "منتج 1 امبول",
    )
    assert not result.accepted
    assert result.rejection_reason == "candidate pack conflicts with requested pack"

    injection_ampoule = validate_product_compatibility(
        "PRODUCT INJECTION",
        "منتج امبول",
    )
    assert not injection_ampoule.accepted
    assert injection_ampoule.rejection_reason == "candidate form conflicts with requested form"


@pytest.mark.parametrize(
    ("query", "candidate"),
    [
        ("VOLTAREN 3AMP", "فولتارين 3مبول"),
        ("VOLTAREN 3 AMP", "فولتارين 3 امبول"),
        ("XITHRONE 500MG 3TAB", "زيثرون 500 مجم 3قرص"),
    ],
)
def test_compact_form_and_pack_tokens_are_compatible(
    query: str, candidate: str
) -> None:
    result = validate_product_compatibility(query, candidate)

    assert result.accepted


@pytest.mark.parametrize(
    ("query", "candidate", "reason"),
    [
        (
            "VOLTAREN 3AMP",
            "فولتارين 6امبولة",
            "candidate pack conflicts with requested pack",
        ),
        (
            "XITHRONE 500MG 3TAB",
            "زيثرون 500 مجم 5قرص",
            "candidate pack conflicts with requested pack",
        ),
        (
            "XITHRONE 500MG 3TAB",
            "زيثرون 500 مجم شراب",
            "candidate form conflicts with requested form",
        ),
    ],
)
def test_compact_variant_negatives_remain_rejected(
    query: str, candidate: str, reason: str
) -> None:
    result = validate_product_compatibility(query, candidate)

    assert not result.accepted
    assert result.rejection_reason == reason
