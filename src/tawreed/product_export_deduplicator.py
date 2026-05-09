"""Deduplication helpers for product exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator


@dataclass(frozen=True)
class ProductIdentity:
    """Immutable product identity key for deduplication."""

    product_name_en: str
    product_name_ar: str
    store_product_id: str

    def is_valid(self) -> bool:
        """Return whether all identity components are non-empty."""
        return bool(
            self.product_name_en.strip()
            and self.product_name_ar.strip()
            and self.store_product_id.strip()
        )


def identity_key(product: dict[str, Any]) -> ProductIdentity:
    """Extract deduplication key from product dict."""
    return ProductIdentity(
        product_name_en=str(product.get("productNameEn") or "").strip(),
        product_name_ar=str(product.get("productName") or "").strip(),
        store_product_id=str(product.get("storeProductId") or "").strip(),
    )


def deduplicate_products(
    products: Iterable[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    """
    Yield unique products based on (nameEn, nameAr, storeProductId).

    Strategy:
    - Use set to track seen identities
    - Keep first occurrence (preserves input sort order)
    - Skip products with null/empty identity fields
    """
    seen: set[ProductIdentity] = set()
    for product in products:
        yield from _deduplicate_one_product(product, seen)


def _deduplicate_one_product(
    product: dict[str, Any], seen: set[ProductIdentity]
) -> Iterator[dict[str, Any]]:
    """Yield product if not a duplicate; mark as seen."""
    key = identity_key(product)
    if not key.is_valid() or key in seen:
        return
    seen.add(key)
    yield product


def deduplicate_products_to_list(
    products: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate products and return as list (for small datasets)."""
    return list(deduplicate_products(products))


def count_duplicates_removed(
    original_count: int, deduplicated_count: int
) -> int:
    """Return number of duplicates removed."""
    return max(0, original_count - deduplicated_count)
