"""Excel catalog loader for the Excel target source.

The Excel target is a pharmacy/vendor pricelist in the shape::

    صنف | سعر | الخصم

(or with an optional leading code column). Each row becomes one
:class:`TargetProduct` so the matching engine can treat the catalog the
same way it treats a Tawreed search response.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, cast

import openpyxl

from ..config.config_models import ExcelTargetConfig


logger = logging.getLogger(__name__)


_IDENTITY_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_identity_component(value: object, *, path: bool = False) -> str:
    """Return a stable, case-insensitive identity component."""
    text = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    if path:
        text = text.replace("\\", "/")
    return _IDENTITY_WHITESPACE_RE.sub(" ", text)


@dataclass(frozen=True)
class TargetProduct:
    """One row of an Excel target catalog, normalised for matching."""

    code: str
    name: str
    price: float | None
    discount_percent: float
    source_file: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    price_meaning: str = "public_with_discount"
    public_price: float | None = None
    purchase_price: float | None = None
    name_en: str | None = None
    source_row_number: int = 0

    @property
    def name_ar(self) -> str:
        """Return the supplier's raw name; it may be Arabic or English."""
        return self.name

    @property
    def trusted_name_en(self) -> str:
        """Return a native English name only; Arabic/mixed cells are not English evidence."""
        if self.name_en:
            return self.name_en
        has_arabic = any("\u0600" <= char <= "\u06ff" for char in self.name)
        has_latin = any(char.isascii() and char.isalpha() for char in self.name)
        return self.name if has_latin and not has_arabic else ""

    @property
    def store_product_id(self) -> str:
        """Return the stable candidate identity used by Excel-target matching."""
        code = str(self.code or "").strip()
        if code:
            return code

        identity_material = "|".join(
            (
                _normalize_identity_component(self.source_file, path=True),
                str(self.source_row_number),
                _normalize_identity_component(self.name),
            )
        )
        return hashlib.sha256(identity_material.encode("utf-8")).hexdigest()

    def to_candidate_dict(self) -> dict[str, Any]:
        """Return the candidate dict shape consumed by the core matcher.

        The matcher reads ``productNameEn``, ``productName``,
        ``availableQuantity``, ``discountPercent`` and ``salePrice`` from
        each candidate. We populate those keys so the same scoring engine
        works on Excel catalog rows without modification.

        The candidate also carries ``priceMeaning`` and (when the catalog
        declares them) explicit ``publicPrice`` / ``salePrice`` columns so
        the pricing resolver knows whether to derive or trust each side.
        """
        candidate: dict[str, Any] = {
            "productNameEn": self.trusted_name_en,
            "productNameEnFallback": self.trusted_name_en,
            "productName": self.name,
            "availableQuantity": 1,
            "productsCount": 1,
            "discountPercent": float(self.discount_percent or 0.0),
            "storeProductId": self.store_product_id,
            "excelTarget": True,
            "excelTargetSourceFile": self.source_file,
            "excelTargetRaw": dict(self.raw),
            "priceMeaning": self.price_meaning,
            "verified_brand_identity": bool(self.trusted_name_en),
            "identity_evidence": "native English supplier name" if self.trusted_name_en else "",
            "identity_evidence_kind": "native_english" if self.trusted_name_en else "",
        }
        # Keep a blank catalog price absent.  Emitting ``0`` for an empty
        # cell would make the pricing resolver treat an unknown offer as a
        # free one and could incorrectly win the cart gate.  ``0`` itself is
        # valid and therefore must remain a real numeric value.
        if self.price is not None:
            if self.price_meaning == "purchase_only":
                candidate["salePrice"] = float(self.price)
            else:
                candidate["price"] = float(self.price)
        if self.public_price is not None:
            candidate["publicPrice"] = float(self.public_price)
            candidate["public_price_col_value"] = float(self.public_price)
        if self.purchase_price is not None:
            candidate["salePrice"] = float(self.purchase_price)
            candidate["purchase_price_col_value"] = float(self.purchase_price)
        return candidate


_HEADER_NORMALIZE_RE = re.compile(r"\s+")


def _normalize_header(value: object) -> str:
    """Normalize one Excel header cell for stable Arabic matching."""
    if value is None:
        return ""
    return _HEADER_NORMALIZE_RE.sub(" ", str(value).strip())


def load_target_catalog_from_excel(
    path: Path,
    config: ExcelTargetConfig,
    source_file: str = "",
) -> list[TargetProduct]:
    """Load the Excel target catalog from ``path`` using ``config``.

    The loader auto-detects the header row by scanning the first
    ``HEADER_SCAN_LIMIT`` rows for the configured ``name_col`` /
    ``price_col`` / ``discount_col`` headers. When the configured
    ``header_row`` is set explicitly it takes precedence and is trusted
    as-is.

    ``source_file`` is an optional label (typically ``Path(path).name``)
    that is recorded on every parsed :class:`TargetProduct` so the
    downstream CSV can preserve provenance when one target key is fed
    by several files (e.g. the operator picked multiple Existing files
    in the GUI).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Excel target file not found: {path}")

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = _select_sheet(workbook, config)
        header_index = _resolve_header_index(sheet, config)
        column_indices = _resolve_column_indices(sheet, header_index, config)
        products: list[TargetProduct] = []
        for source_row_number, row in enumerate(
            sheet.iter_rows(min_row=header_index + 2, values_only=True),
            start=header_index + 2,
        ):
            product = _row_to_product(
                row,
                column_indices,
                config,
                source_file,
                source_row_number,
            )
            if product is not None:
                products.append(product)
        return products
    finally:
        workbook.close()


HEADER_SCAN_LIMIT = 10


def _select_sheet(workbook, config: ExcelTargetConfig):
    """Return the worksheet the catalog lives in."""
    if config.sheet:
        if config.sheet in workbook.sheetnames:
            return workbook[config.sheet]
        raise ValueError(
            f"Excel target sheet '{config.sheet}' not found. "
            f"Available sheets: {workbook.sheetnames}"
        )
    return workbook.active


def _resolve_header_index(sheet, config: ExcelTargetConfig) -> int:
    """Find the row index that contains the configured headers."""
    if config.header_row:
        return int(config.header_row)

    name_alias = _normalize_header(config.name_col)
    price_alias = _normalize_header(config.price_col)
    discount_alias = _normalize_header(config.discount_col)
    for row_index, row in enumerate(
        cast(Any, sheet).iter_rows(
            max_row=HEADER_SCAN_LIMIT, values_only=True
        )
    ):
        normalized = {_normalize_header(cell) for cell in row if cell is not None}
        if name_alias in normalized and (
            price_alias in normalized or discount_alias in normalized
        ):
            return row_index
    return 0


def _resolve_column_indices(
    sheet, header_index: int, config: ExcelTargetConfig
) -> dict[str, int]:
    """Map configured column names to numeric indices on the header row."""
    header_row = list(
        cast(Any, sheet).iter_rows(
            min_row=header_index + 1,
            max_row=header_index + 1,
            values_only=True,
        )
    )[0]
    col_map: dict[str, int] = {}
    for idx, cell in enumerate(header_row):
        key = _normalize_header(cell)
        if key:
            col_map[key] = idx

    indices: dict[str, int] = {}
    for logical, configured in (
        ("name", config.name_col),
        ("price", config.price_col),
        ("discount", config.discount_col),
        ("code", config.code_col),
    ):
        if not configured:
            continue
        key = _normalize_header(configured)
        if key not in col_map:
            raise ValueError(
                f"Excel target column '{configured}' not found in header row. "
                f"Found headers: {sorted(col_map)}"
            )
        indices[logical] = col_map[key]
    return indices


def _row_to_product(
    row: tuple,
    indices: dict[str, int],
    config: ExcelTargetConfig,
    source_file: str = "",
    source_row_number: int = 0,
) -> TargetProduct | None:
    """Convert one Excel row tuple into a TargetProduct."""
    name_cell = row[indices["name"]] if "name" in indices else None
    name = str(name_cell or "").strip()
    if not name:
        return None

    raw: dict[str, Any] = {"name": name}
    price: float | None = None
    if "price" in indices:
        price = _to_float(row[indices["price"]])
        raw["price"] = price

    discount = 0.0
    if "discount" in indices:
        discount = _to_float(row[indices["discount"]]) or 0.0
        raw["discount"] = discount

    code = ""
    if "code" in indices:
        code = str(row[indices["code"]] or "").strip()
        raw["code"] = code
    if not code and config.requires_code:
        return None

    return TargetProduct(
        code=code,
        name=name,
        price=price,
        discount_percent=discount,
        source_file=source_file,
        source_row_number=source_row_number,
        raw=raw,
        price_meaning=getattr(config, "price_meaning", "public_with_discount"),
    )


def _to_float(value: Any) -> float | None:
    """Coerce one Excel cell to ``float`` while preserving empty cells.

    The caller decides whether a missing value is allowed to default (the
    discount column does) or must remain unknown (the price column does).
    Numeric zero is intentionally returned unchanged.
    """
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        text = str(value).strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None


def iter_target_candidates(
    products: Iterable[TargetProduct],
) -> list[dict[str, Any]]:
    """Materialise an iterable of products into candidate dicts."""
    return [product.to_candidate_dict() for product in products]


__all__ = [
    "TargetProduct",
    "load_target_catalog_from_excel",
    "iter_target_candidates",
]
