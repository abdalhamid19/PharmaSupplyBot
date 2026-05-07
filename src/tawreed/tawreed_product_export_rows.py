"""Row normalization helpers for Tawreed product catalog exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator

EXPORT_FIELDNAMES = ("product_name_ar", "product_name_en", "store_product_id")


@dataclass(frozen=True)
class ProductExportRow:
    """One normalized Tawreed store-product row for catalog exports."""

    product_name_ar: str
    product_name_en: str
    store_product_id: str

    def as_dict(self) -> dict[str, str]:
        """Return this row using the stable export field names."""
        return {
            "product_name_ar": self.product_name_ar,
            "product_name_en": self.product_name_en,
            "store_product_id": self.store_product_id,
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
        identity = tuple(row.values())
        if identity == ("", "", "") or identity in seen:
            continue
        seen.add(identity)
        yield row


def _row_from_candidate(candidate: dict[str, Any]) -> ProductExportRow:
    return ProductExportRow(
        product_name_ar=str(candidate.get("productName") or "").strip(),
        product_name_en=str(candidate.get("productNameEn") or "").strip(),
        store_product_id=str(candidate.get("storeProductId") or "").strip(),
    )
