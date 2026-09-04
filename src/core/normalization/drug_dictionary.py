"""Egyptian drug brand-name dictionary.

Loads ``data/input/dictionaries/egyptian_drugs.csv`` (CC0 from
``karem505/egyptian-drug-database``) once and exposes three indices for
fast lookup:

* ``by_en``  — normalized English trade name → list of (Arabic, manufacturer, …)
* ``by_ar``  — normalized Arabic trade name → list of (English, manufacturer, …)
* ``by_scientific`` — scientific name → list of (English, Arabic, manufacturer)

The loader is process-wide cached so subsequent runs don't re-parse
the 25k-row CSV.
"""
from __future__ import annotations

import csv
import logging
import re
import threading
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


DEFAULT_CSV = Path("data/input/dictionaries/egyptian_drugs.csv")


_PUNCT_RE = re.compile(r"[^A-Za-z0-9\u0600-\u06FF]+")
_DIGIT_RE = re.compile(r"\d")


def _normalize_en(name: str) -> str:
    """Normalize an English drug name to a stable lookup key.

    Drops strength (e.g. ``400 MG``), form tokens (``TAB``, ``CAP``,
    ``CREAM``), pack size (``30 TABS``) and punctuation. What remains is
    the brand prefix used for dictionary lookup.
    """
    s = name.upper()
    s = re.sub(r"\b\d+\s*(MG|GM|G|ML|MCG|IU|%|MCG)\b", " ", s)
    s = re.sub(
        r"\b(TAB|TABS|TABLET|TABLETS|CAP|CAPS|CAPSULE|CAPSULES|"
        r"CREAM|GEL|OINT|SYRUP|SUSP|INJ|INJECTION|DROPS|SPRAY|"
        r"SACHET|SUPP|F\.?C\.?|EFFER|LOZ|LOZENGE|MILK|POWDER|"
        r"GRANULES|SOLUTION|EMULSION|GUM|MOUTHWASH|LOZENGES|FILM|"
        r"FILMS)\b\.?",
        " ",
        s,
    )
    s = _PUNCT_RE.sub(" ", s)
    s = _DIGIT_RE.sub("", s)
    return _WHITESPACE_RE.sub(" ", s).strip()


def _normalize_ar(name: str) -> str:
    """Normalize an Arabic drug name to a stable lookup key."""
    s = name.strip()
    s = _PUNCT_RE.sub(" ", s)
    return _WHITESPACE_RE.sub(" ", s).strip()


_WHITESPACE_RE = re.compile(r"\s+")


@lru_cache(maxsize=1)
def load_dictionary(csv_path: str = "") -> dict[str, list[dict[str, str]]]:
    """Load the drug dictionary from disk and return all three indices.

    Returns ``{"by_en": {...}, "by_ar": {...}, "by_scientific": {...}}``.
    When the CSV is missing or empty, returns empty indices.
    """
    path = Path(csv_path) if csv_path else DEFAULT_CSV
    if not path.exists():
        logger.warning("drug dictionary csv missing: %s", path)
        return {"by_en": {}, "by_ar": {}, "by_scientific": {}}

    by_en: dict[str, list[dict[str, str]]] = {}
    by_ar: dict[str, list[dict[str, str]]] = {}
    by_scientific: dict[str, list[dict[str, str]]] = {}

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            en = (row.get("commercial_name_en") or "").strip()
            ar = (row.get("commercial_name_ar") or "").strip()
            sci = (row.get("scientific_name") or "").strip()
            manufacturer = (row.get("manufacturer") or "").strip()
            drug_class = (row.get("drug_class") or "").strip()
            route = (row.get("route") or "").strip()
            if not en and not ar:
                continue
            record = {
                "en": en,
                "ar": ar,
                "scientific": sci,
                "manufacturer": manufacturer,
                "drug_class": drug_class,
                "route": route,
            }
            en_key = _normalize_en(en)
            if en_key:
                by_en.setdefault(en_key, []).append(record)
            ar_key = _normalize_ar(ar)
            if ar_key:
                by_ar.setdefault(ar_key, []).append(record)
            sci_key = sci.lower()
            if sci_key:
                by_scientific.setdefault(sci_key, []).append(record)

    logger.info(
        "drug dictionary loaded: %d EN keys, %d AR keys, %d scientific keys",
        len(by_en),
        len(by_ar),
        len(by_scientific),
    )
    return {"by_en": by_en, "by_ar": by_ar, "by_scientific": by_scientific}


def lookup_en(name: str) -> list[dict[str, str]]:
    """Return all Arabic aliases registered for the given English brand."""
    return load_dictionary()["by_en"].get(_normalize_en(name), [])


def lookup_ar(name: str) -> list[dict[str, str]]:
    """Return all English aliases registered for the given Arabic brand."""
    return load_dictionary()["by_ar"].get(_normalize_ar(name), [])
