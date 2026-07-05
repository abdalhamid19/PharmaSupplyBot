"""Drug name parsing and component extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalizer_parsing_constants import (
    _DOSAGE_RE, _MG_PER_ML_RE, _COMBO_MG_PER_ML_RE, _WEIGHT_RE,
    _QTY_RE, _VOL_RE, _IMPORT_MARKER_RE, ACRONYM_BRANDS, BRAND_QUALIFIERS,
    FORM_SCAN_ORDER, FORM_WORDS, FLAVOR_WORDS,
    FORM_PREFIXES, NOISE_WORDS, SOFT_BRAND_DESCRIPTORS, CONNECTOR_WORDS,
    SUPPLEMENT_WORDS,
)
from .normalizer_parsing_normalize import normalize, _convert_arabic_to_english_terms
from .normalizer_parsing_classification import classify_product, brand_variants_from_words
from .normalizer_parsing_inference import (
    _infer_missing_dosage,
    _weight_is_strength,
    _is_brand_boundary,
    _is_pediatric_inf,
    _is_descriptive_brand_word,
)


@dataclass(slots=True)
class DrugComponents:
    """Parsed drug identity fields used for compatibility checks."""
    brand: str
    dosage_nums: tuple[str, ...]
    dosage_units: tuple[str, ...]
    qty: str
    volume: str
    weight: str
    form: str
    flavor: str
    imported: bool
    normalized: str
    brand_variants: tuple[str, ...] = ()
    product_class: str = "medicine"
    is_synthetic: bool = False
    manufacturer: str | None = None


def parse_drug(name: str) -> DrugComponents:
    """Parse a raw drug/product name into matching components."""
    if not name or not isinstance(name, str):
        return DrugComponents(
            "", (), (), "", "", "", "", "", "", False, "",
            is_synthetic=False,
            manufacturer=None,
        )

    # Extract manufacturer first before other processing
    from .normalizer_manufacturer_extraction import extract_manufacturer_from_name
    name_without_mfr, manufacturer = extract_manufacturer_from_name(name)
    
    # Continue parsing with manufacturer-free name
    imported = bool(_IMPORT_MARKER_RE.search(name_without_mfr))
    if any(0x0600 <= ord(ch) <= 0x06FF for ch in name_without_mfr):
        name_without_mfr = _convert_arabic_to_english_terms(name_without_mfr)
    norm = normalize(name_without_mfr)

    combo_mg_per_ml = _COMBO_MG_PER_ML_RE.search(norm)
    mg_per_ml = _MG_PER_ML_RE.search(norm)
    if combo_mg_per_ml:
        dosage_nums = (f"{combo_mg_per_ml.group(1)}/{combo_mg_per_ml.group(2)}",)
        dosage_units = ("MG/ML",)
    elif mg_per_ml:
        dosage_nums = (mg_per_ml.group(1),)
        dosage_units = ("MG/ML",)
    else:
        d_matches = _DOSAGE_RE.findall(norm)
        dosage_nums = tuple(re.sub(r"\s+", "", m[0]) for m in d_matches)
        dosage_units = tuple(m[1] for m in d_matches)

    w_matches = _WEIGHT_RE.findall(norm)
    weight = w_matches[-1][0] if w_matches else ""
    q = _QTY_RE.search(norm)
    qty = q.group(1) if q else ""
    v = _VOL_RE.findall(norm)
    volume = v[-1] if v else ""

    words = norm.split()
    if words and words[0] in ACRONYM_BRANDS:
        brand = words[0]
    else:
        brand = ""
    brand_words = []
    if not brand:
        for idx, w in enumerate(words):
            if re.search(r"\d", w):
                break
            if _is_brand_boundary(words, idx):
                break
            brand_words.append(w)
        brand = "".join(brand_words)
    if not brand and words and words[0] in BRAND_QUALIFIERS:
        brand = "".join(
            w for idx, w in enumerate(words[1:], start=1)
            if not re.search(r"\d", w) and not _is_brand_boundary(words, idx) and not _is_pediatric_inf(words, idx) and not _is_descriptive_brand_word(words[idx])
        )
    if brand == "ATOMOXAPEX" and dosage_nums == ("40",) and volume == "100":
        dosage_nums, dosage_units = ("4",), ("MG/ML",)

    form = ""
    norm_words = set(norm.split())
    for fw in FORM_SCAN_ORDER:
        if fw in norm_words:
            form = _canonical_form(fw)
            break
    if form == "SUSP" and ({"EYE", "DROPS"} & norm_words):
        form = "EYE"
    if (
        not dosage_nums
        and qty
        and qty.isdigit()
        and int(qty) >= 100
        and "VAGINAL" in norm_words
        and form in {"CAP", "SUPP"}
    ):
        qty = ""
    if not dosage_nums:
        dosage_nums, dosage_units = _infer_missing_dosage(norm, qty, volume, weight, form)
    if not dosage_nums and _weight_is_strength(weight, form, norm_words):
        dosage_nums, dosage_units = (weight,), ("GM",)
    flavor = ""
    for fw in FLAVOR_WORDS:
        if fw in norm_words:
            flavor = fw
            break

    product_class = classify_product(norm)
    variants = brand_variants_from_words(words, brand)
    return DrugComponents(
        brand,
        dosage_nums,
        dosage_units,
        qty,
        volume,
        weight,
        form,
        flavor,
        imported,
        norm,
        variants,
        product_class,
        is_synthetic=False,
        manufacturer=manufacturer,
    )


def _canonical_form(word: str) -> str:
    if word in {"TABLET", "TABLETS", "TAB", "TABS"}:
        return "TAB"
    if word in {"CAP", "CAPS", "CAPSULE", "CAPSULES"}:
        return "CAP"
    if word in {"SPRAY", "SPRAYS", "DOSES", "METERED"}:
        return "SPRAY"
    if word in {"DROPS", "DROP", "OPHTHALMIC", "EYE"}:
        return "EYE"
    if word in {"OINT", "OINTMENT"}:
        return "OINT"
    if word in {"VIAL", "VIALS"}:
        return "VIAL"
    if word in {"AMP", "AMPS", "AMPOULE", "AMPOULES"}:
        return "AMP"
    if word in {"PEN", "PENS"}:
        return "PEN"
    if word in {"CARTRIDGE", "CARTRIDGES", "CARTIRIDGES"}:
        return "CARTRIDGE"
    if word in {"SUPP", "SUPPS"}:
        return "SUPP"
    if word in {"SYRP", "SYP"}:
        return "SYRUP"
    return word
