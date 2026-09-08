"""Contracts for strict medicine-variant compatibility."""

from src.core.excel_target.product_attributes import validate_product_compatibility


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
