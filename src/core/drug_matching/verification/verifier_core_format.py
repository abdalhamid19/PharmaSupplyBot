"""Candidate formatting and component context functions for AI verifier module."""

from __future__ import annotations

from ..normalization.normalizer import parse_drug


def route_from_norm(norm: str) -> str:
    """Extract route (IM/IV/SC) from normalized drug name."""
    words = set(norm.split())
    routes = set(words & {"IM", "IV", "SC"})
    if {"I", "M"} <= words:
        routes.add("IM")
    if {"I", "V"} <= words:
        routes.add("IV")
    if {"S", "C"} <= words:
        routes.add("SC")
    return "/".join(sorted(routes)) or "-"


def component_context(name: str) -> str:
    """Return formatted component context string for a drug name."""
    c = parse_drug(name)
    return (
        f"normalized='{c.normalized}', brand='{c.brand}', "
        f"dosage={c.dosage_nums or '-'}, qty='{c.qty or '-'}', "
        f"volume='{c.volume or '-'}', weight='{c.weight or '-'}', "
        f"form='{c.form or '-'}', flavor='{c.flavor or '-'}', "
        f"class='{c.product_class}', "
        f"route='{route_from_norm(c.normalized)}', "
        f"imported={'yes' if c.imported else 'no'}"
    )


def format_candidate(
    position: int, candidate: tuple[dict, float, int],
    inventory_price=None,
) -> str:
    """Format a candidate with position, score, price, and component context."""
    from ..pricing import format_price, price_delta_text
    rec, score, _ = candidate[:3]
    review_reason = candidate[3] if len(candidate) > 3 else "ok"
    if review_reason == "ok":
        review_text = ""
    else:
        review_text = (
            f"\n   rule_review: candidate entered AI review despite {review_reason}; "
            "accept only if the products are truly equivalent"
        )
    candidate_price = rec.get("price")
    price_text = (
        f", candidate_price={format_price(candidate_price)}, "
        f"price_delta={price_delta_text(inventory_price, candidate_price)}"
    )
    return (
        f"{position}. {rec['product_name_en']} / "
        f"{rec.get('product_name_ar', '')} "
        f"(score={score:.1f}{price_text})\n"
        f"   parsed: {component_context(rec['product_name_en'])}"
        f"{review_text}"
    )


__all__ = [
    "route_from_norm",
    "component_context",
    "format_candidate",
]
