"""Single resolver for store pricing across sources.

Every snapshot row in ``run_item_stores`` must carry both
``public_price`` (retail) and ``purchase_price`` (what the pharmacy pays),
plus a ``discount_percent`` and a derived ``net_price`` (purchase after
discount). Tawreed rows come with both prices explicitly; Excel-target
rows come with a single price column whose meaning depends on the
catalog's ``priceMeaning`` flag.

This module owns the one rule that turns a candidate dict into those four
values, so the rest of the codebase reads the resolved shape and never
re-derives anything. ``price_provenance`` records which rule fired so the
UI can warn the user when public and purchase were synthesised rather
than read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


PriceProvenance = Literal[
    "tawreed_both",
    "tawreed_public_only",
    "tawreed_purchase_only",
    "excel_public_implies_purchase",
    "excel_purchase_implies_public",
    "excel_both",
    "unknown",
]

PROVENANCE_LABELS: dict[PriceProvenance, str] = {
    "tawreed_both": "👤 Tawreed",
    "tawreed_public_only": "👤 Tawreed (public only)",
    "tawreed_purchase_only": "👤 Tawreed (purchase only)",
    "excel_public_implies_purchase": "📊 Excel (public → purchase)",
    "excel_purchase_implies_public": "📊 Excel (purchase → public)",
    "excel_both": "📊 Excel (both prices)",
    "unknown": "—",
}

SourceKind = Literal["tawreed", "excel_target"]

DEFAULT_EXCEL_PRICE_MEANING: Literal[
    "public_with_discount", "purchase_only", "public_only"
] = "public_with_discount"


@dataclass(frozen=True)
class ResolvedPrices:
    """The four normalised price values plus a provenance tag."""

    public_price: float | None
    purchase_price: float | None
    discount_percent: float
    net_price: float | None
    price_provenance: PriceProvenance


def _first_present(store: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    """Return the first non-empty numeric value among ``keys``, else ``None``."""
    from ..database.order_runs_values import as_optional_float

    for key in keys:
        value = as_optional_float(store.get(key))
        if value is not None:
            return value
    return None


def _read_discount(store: dict[str, Any]) -> float:
    """Return the discount percent using the shared Tawreed helper."""
    from ..database.order_runs_store_values import discount_percent_value

    return discount_percent_value(store)


def _net_price(
    purchase: float | None,
    public: float | None,
    discount: float,
    provenance: PriceProvenance = "unknown",
) -> float | None:
    """Return the price the pharmacy effectively pays.

    Two cases:
    - Tawreed (or any row with both prices set independently): the API
      already returns the discounted purchase price, so ``net`` equals
      ``purchase``.
    - Excel target with a single column (``excel_public_implies_purchase``
      or ``excel_purchase_implies_public``): the column already encodes
      the public price, and the resolver derives purchase from it. The
      net therefore equals ``purchase`` too — applying the discount
      again would double-count it.
    - When only ``public`` is known: ``net = public × (1 − discount)``.
    """
    if purchase is not None:
        return round(purchase, 2)
    if public is not None:
        rate = max(0.0, 1.0 - discount / 100.0)
        return round(public * rate, 2)
    return None


def resolve_store_prices(
    store: dict[str, Any],
    *,
    source_kind: SourceKind = "tawreed",
    excel_price_meaning: Literal[
        "public_with_discount", "purchase_only", "public_only"
    ] = DEFAULT_EXCEL_PRICE_MEANING,
) -> ResolvedPrices:
    """Return the resolved public/purchase/discount/net for one store row.

    ``source_kind`` selects the derivation policy. The two relevant cases:

    - ``"tawreed"``: trust the two distinct fields. If only one is present
      the missing side stays ``None``; nothing is invented.
    - ``"excel_target"``: honour ``excel_price_meaning``. The default
      ``"public_with_discount"`` assumes the single price column is the
      retail price; ``purchase_price`` is then computed as
      ``public × (1 − discount)`` and ``public`` is left intact. Other
      meanings (``"purchase_only"`` / ``"public_only"``) skip the
      derivation and keep the missing side ``None``.
    """
    from ..database.order_runs_store_values import (
        PUBLIC_PRICE_KEYS,
        PURCHASE_PRICE_KEYS,
    )

    public_raw = _first_present(store, PUBLIC_PRICE_KEYS)
    purchase_raw = _first_present(store, PURCHASE_PRICE_KEYS)
    discount = _read_discount(store)

    if source_kind == "tawreed":
        public_price: float | None = public_raw
        purchase_price: float | None = purchase_raw
        if public_price is not None and purchase_price is not None:
            provenance: PriceProvenance = "tawreed_both"
        elif public_price is not None:
            provenance = "tawreed_public_only"
        elif purchase_price is not None:
            provenance = "tawreed_purchase_only"
        else:
            provenance = "unknown"
    else:
        explicit_public_col = bool(store.get("public_price_col_value") is not None) or (
            "publicPrice" in store or "retailPrice" in store
        )
        explicit_purchase_col = bool(
            store.get("purchase_price_col_value") is not None
        )

        if explicit_public_col and explicit_purchase_col:
            public_price = public_raw
            purchase_price = purchase_raw
            provenance = "excel_both"
        elif explicit_purchase_col and purchase_raw is not None:
            purchase_price = purchase_raw
            public_price = purchase_price
            provenance = "excel_purchase_implies_public"
        elif explicit_public_col and public_raw is not None:
            public_price = public_raw
            purchase_price = round(public_price * (1.0 - discount / 100.0), 2)
            provenance = "excel_public_implies_purchase"
        elif excel_price_meaning == "purchase_only":
            purchase_price = purchase_raw if purchase_raw is not None else public_raw
            public_price = purchase_price if purchase_price is not None else None
            if purchase_price is not None and public_price is not None:
                provenance = "excel_purchase_implies_public"
            else:
                provenance = "unknown"
        else:
            public_price = public_raw
            if public_price is not None and purchase_raw is None:
                if excel_price_meaning == "public_only":
                    purchase_price = None
                    provenance = "tawreed_public_only"
                else:
                    purchase_price = round(public_price * (1.0 - discount / 100.0), 2)
                    provenance = "excel_public_implies_purchase"
            elif purchase_raw is not None and public_price is None:
                purchase_price = purchase_raw
                provenance = "excel_purchase_implies_public"
            elif purchase_raw is not None and public_price is not None:
                purchase_price = purchase_raw
                provenance = "excel_purchase_implies_public"
            else:
                purchase_price = None
                provenance = "unknown"

    net = _net_price(purchase_price, public_price, discount, provenance)

    return ResolvedPrices(
        public_price=public_price,
        purchase_price=purchase_price,
        discount_percent=discount,
        net_price=net,
        price_provenance=provenance,
    )


def resolved_to_store_price_fields(resolved: ResolvedPrices) -> dict[str, Any]:
    """Project a : ``ResolvedPrices`` onto the legacy ``run_item_stores`` columns."""
    return {
        "public_price": resolved.public_price,
        "purchase_price": resolved.purchase_price,
        "discount_percent": resolved.discount_percent,
    }


__all__ = [
    "DEFAULT_EXCEL_PRICE_MEANING",
    "PriceProvenance",
    "PROVENANCE_LABELS",
    "ResolvedPrices",
    "SourceKind",
    "resolve_store_prices",
    "resolved_to_store_price_fields",
]