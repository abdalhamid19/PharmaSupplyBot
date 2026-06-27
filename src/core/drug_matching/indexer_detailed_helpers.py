"""Helper functions for detailed matching."""

from .pricing import parse_price


def _parse_price(value) -> float | None:
    """Parse price value."""
    return parse_price(value)


def _price_bonus(query_price, candidate_price) -> float:
    """Calculate price-based score bonus."""
    if query_price is None or candidate_price is None:
        return 0.0
    diff_ratio = abs(query_price - candidate_price) / max(
        query_price,
        candidate_price,
    )
    if diff_ratio == 0:
        return 6.0
    if diff_ratio <= 0.02:
        return 5.0
    if diff_ratio <= 0.05:
        return 4.0
    if diff_ratio <= 0.10:
        return 2.0
    return 0.0


def _forms_match(left: str, right: str) -> bool:
    """Check if two forms match (including ocular forms)."""
    from .normalizer import OCULAR_FORMS
    if left == right:
        return True
    return bool(left in OCULAR_FORMS and right in OCULAR_FORMS)


def _display_score(score: float) -> float:
    """Display score capped at 100."""
    return min(score, 100.0)


__all__ = [
    "_parse_price",
    "_price_bonus",
    "_forms_match",
    "_display_score",
]
