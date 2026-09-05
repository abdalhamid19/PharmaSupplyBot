"""Tawreed product catalog loader.

Loads ``data/input/dictionaries/tawreed_products.csv`` (49K products
with Arabic+English trade names + store_product_id) and exposes it as
two indices for fast lookup:

* ``by_ar`` — collapsed Arabic trade name → English trade name + IDs
* ``by_en`` — collapsed English trade name → Arabic trade name + IDs

The catalog is the cheapest and highest-quality source of drug-name
translations because every row has been verified by Tawreed's product
team. The ``bilingual_brand_matcher`` consults this first before
falling back to the karem505 community dataset or Cohere.

The CSV format::

    product_name_ar,product_name_en,store_product_id,product_id,sale_price
    1 2 3 ...,1 2 3 ONE TWO THREE 20 F.C. TAB,2437679.0,80009.0,40.0
"""
from __future__ import annotations

import csv
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


DEFAULT_CSV = Path("data/input/dictionaries/tawreed_products.csv")


_WHITESPACE_RE = re.compile(r"\s+")


def collapse_ws(s: str) -> str:
    """Collapse runs of whitespace to single spaces + trim.

    Used as the join key for both Arabic and English columns so a
    product whose spreadsheet cell has trailing spaces, double
    spaces or newlines still matches its registry row.
    """
    if not s:
        return ""
    return _WHITESPACE_RE.sub(" ", str(s)).strip()


@lru_cache(maxsize=1)
def load_tawreed_catalog(csv_path: str = "") -> dict[str, Any]:
    """Load the Tawreed catalog and return both indices + the raw rows.

    Returns ``{"by_ar": {...}, "by_en": {...}, "rows": [...]}``.

    When the CSV is missing, returns empty indices. The function is
    ``@lru_cache``'d so subsequent calls in the same process reuse
    the parsed result.
    """
    path = Path(csv_path) if csv_path else DEFAULT_CSV
    by_ar: dict[str, list[dict[str, str]]] = {}
    by_en: dict[str, list[dict[str, str]]] = {}
    rows: list[dict[str, str]] = []
    if not path.exists():
        logger.warning("tawreed catalog csv missing: %s", path)
        return {"by_ar": by_ar, "by_en": by_en, "rows": rows}

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ar = collapse_ws(row.get("product_name_ar", ""))
            en = collapse_ws(row.get("product_name_en", ""))
            if not ar and not en:
                continue
            record = {
                "ar": ar,
                "en": en,
                "store_product_id": (row.get("store_product_id") or "").strip(),
                "product_id": (row.get("product_id") or "").strip(),
                "sale_price": (row.get("sale_price") or "").strip(),
            }
            rows.append(record)
            if ar:
                by_ar.setdefault(ar, []).append(record)
            if en:
                by_en.setdefault(en, []).append(record)

    logger.info(
        "tawreed catalog loaded: %d rows, %d ar keys, %d en keys",
        len(rows),
        len(by_ar),
        len(by_en),
    )
    return {"by_ar": by_ar, "by_en": by_en, "rows": rows}


def lookup_by_arabic(ar_name: str) -> list[dict[str, str]]:
    """Return all Tawreed rows whose Arabic name collapses to ``ar_name``."""
    return load_tawreed_catalog()["by_ar"].get(collapse_ws(ar_name), [])


def lookup_by_english(en_name: str) -> list[dict[str, str]]:
    """Return all Tawreed rows whose English name collapses to ``en_name``."""
    return load_tawreed_catalog()["by_en"].get(collapse_ws(en_name), [])


__all__ = [
    "load_tawreed_catalog",
    "lookup_by_arabic",
    "lookup_by_english",
    "collapse_ws",
    "DEFAULT_CSV",
]
