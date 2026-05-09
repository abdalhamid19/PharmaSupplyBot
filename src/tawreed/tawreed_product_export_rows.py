"""Row normalization helpers for Tawreed product catalog exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator

EXPORT_FIELDNAMES = (
    "product_name_ar",
    "product_name_en",
    "store_product_id",
    "product_id",
    "available_quantity",
    "sale_price",
    "discount_percent",
    "currency",
    "store_name",
    "supplier_name",
)


@dataclass(frozen=True)
class ProductExportRow:
    """One normalized Tawreed store-product row for catalog exports."""

    product_name_ar: str
    product_name_en: str
    store_product_id: str
    product_id: str = ""
    available_quantity: str = ""
    sale_price: str = ""
    discount_percent: str = ""
    currency: str = ""
    store_name: str = ""
    supplier_name: str = ""

    def as_dict(self) -> dict[str, str]:
        """Return this row using the stable export field names."""
        return {
            "product_name_ar": self.product_name_ar,
            "product_name_en": self.product_name_en,
            "store_product_id": self.store_product_id,
            "product_id": self.product_id,
            "available_quantity": self.available_quantity,
            "sale_price": self.sale_price,
            "discount_percent": self.discount_percent,
            "currency": self.currency,
            "store_name": self.store_name,
            "supplier_name": self.supplier_name,
        }

    def values(self) -> list[str]:
        """Return row values in the stable export field order."""
        return [self.as_dict()[field] for field in EXPORT_FIELDNAMES]


def product_export_rows(
    candidates: Iterable[dict[str, Any]],
) -> Iterator[ProductExportRow]:
    """Yield unique normalized rows from Tawreed API product candidates."""
    seen: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        row = _row_from_candidate(candidate)
        identity = _row_identity(row)
        if identity == ("", "", "") or identity in seen:
            continue
        seen.add(identity)
        yield row


def _row_identity(row: ProductExportRow) -> tuple[str, str, str]:
    product_key = row.store_product_id or row.product_id
    return row.product_name_ar, row.product_name_en, product_key


def _row_from_candidate(candidate: dict[str, Any]) -> ProductExportRow:
    return ProductExportRow(
        product_name_ar=str(candidate.get("productName") or "").strip(),
        product_name_en=str(candidate.get("productNameEn") or "").strip(),
        store_product_id=str(candidate.get("storeProductId") or "").strip(),
        product_id=str(candidate.get("productId") or "").strip(),
        available_quantity=str(candidate.get("availableQuantity")
                                or "").strip(),
        sale_price=str(candidate.get("salePrice") or "").strip(),
        discount_percent=str(candidate.get("discountPercent")
                              or "").strip(),
        currency=str(candidate.get("currency") or "").strip(),
        store_name=str(candidate.get("storeName") or "").strip(),
        supplier_name=str(candidate.get("supplierName") or "").strip(),
    )
