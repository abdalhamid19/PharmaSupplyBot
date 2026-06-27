"""Drug name parsing and normalization functions."""

import re
from dataclasses import dataclass
from .normalizer_constants import (
    ACRONYM_BRANDS, BRAND_QUALIFIERS, FLAVOR_WORDS, FORM_PREFIXES,
    FORM_SCAN_ORDER, FORM_WORDS, INFUSION_CONTEXT_WORDS, LIQUID_DOSE_FORMS,
    NOISE_WORDS, PEDIATRIC_WORDS, SOFT_BRAND_DESCRIPTORS, SUPPLEMENT_WORDS,
    BABY_FOOD_WORDS, COSMETIC_WORDS, DEVICE_WORDS, CONNECTOR_WORDS
)

_DOSAGE_RE = re.compile(
    r"(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?(?:\s\d{3})?)\s*(MG|MCG|I\s*U|IU|%)(?=$|\s)",
    re.IGNORECASE
)
_MG_PER_ML_RE = re.compile(r"(\d+(?:\.\d+)?)\s*MG\s*/\s*(\d+(?:\.\d+)?)\s*ML", re.IGNORECASE)
_COMBO_MG_PER_ML_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*MG\s*/\s*(\d+(?:\.\d+)?)\s*ML",
    re.IGNORECASE
)
_WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(GM|G)\b", re.IGNORECASE)
_QTY_RE = re.compile(
    r"(\d+)\s*(?:(?:F\s*C|FC|SCORED|CHEWABLE|EFF|EFFERVESCENT|VAGINAL|VAG|PRE\s*FILLED|PREFILLED|METERED)\s*)?"
    r"(TABLETS|TABLET|TABS|TAB|CAPSULES|CAPSULE|CAPS|CAP|SACHETS|SACHET|SACH|AMPOULES|AMPOULE|AMPS|AMP|VIAL|"
    r"SUPPS|SUPP|PIECE|DROPS|PENS|PEN|CARTRIDGES|CARTIRIDGES|CARTRIDGE|SYRINGES|SYRINGE|GUMMIES|GUM|PACKETS|"
    r"DOSES|METERED)\b",
    re.IGNORECASE
)
_VOL_RE = re.compile(r"(\d+(?:\.\d+)?)\s*ML\b", re.IGNORECASE)
_NOISE_PREFIX_RE = re.compile(r"^[+*.]+\s*(IMP|IMPORTED)?\s*", re.IGNORECASE)
_IMPORT_MARKER_RE = re.compile(r"(^[+*.]+\s*(IMP|IMPORTED))|\b(IMP|IMPORTED)\b", re.IGNORECASE)
_AR_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670]")


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


def normalize_arabic(name: str) -> str:
    """Normalize Arabic product text for auxiliary matching signals."""
    if not name or not isinstance(name, str):
        return ""
    text = _AR_DIACRITICS_RE.sub("", name.strip())
    text = re.sub("[إأآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي").replace("ة", "ه")
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize(name: str) -> str:
    """Normalize an English drug/product name before parsing or fuzzy matching."""
    if not name or not isinstance(name, str):
        return ""
    name = name.strip().upper()
    name = _NOISE_PREFIX_RE.sub("", name)
    name = name.replace("_", " ").replace("\\", " / ")
    name = re.sub(r"-+", " ", name)
    name = re.sub(r"[()]", " ", name)
    name = re.sub(r"(?<=\d)O(?=\d)", "0", name)
    name = re.sub(r"\bFORET\b", "FORTE", name)
    name = re.sub(r"\b(SYRP|SYP)\b", "SYRUP", name)
    name = re.sub(r"\bVAG\b", "VAGINAL", name)
    name = name.replace("*", " / ")
    name = re.sub(r"(?<=\d)O(?=\s*ML\b)", "0", name)
    name = re.sub(r"(?<=%)([A-Z])", r" \1", name)
    name = re.sub(r"([A-Z])(?=\d)", r"\1 ", name)
    name = re.sub(r"(?<=\d)([A-Z])", r" \1", name)
    name = re.sub(r"\b(\d+)\s*M\b(?!\s*\.)", r"\1 MG", name)
    name = re.sub(r"\b(\d+)\s*M\s*/", r"\1 MG /", name)
    name = re.sub(r"\bANDOFLOZIN XR 25 MG\s*/\s*100 MG\b", "ANDOFLOZIN XR 25 / 1000 MG", name)
    name = re.sub(r"\b([BD])\s+(3|6|12)\b", r"\1\2", name)
    name = re.sub(r"\s*[\\/]\s*", " / ", name)
    name = re.sub(r"(\d)\.(\d{3})\s*(I\.?U\.?|IU|MCG|MG)", r"\1\2 \3", name)
    name = re.sub(r"(?<!\d)\.(\d+)", r"0.\1", name)
    name = re.sub(r"\.(?!\d)", " ", name)
    name = re.sub(r"(?<!\d)\.", " ", name)
    name = re.sub(r"\b([DESCMX])\s+R\b", r"\1R", name)
    name = re.sub(r"\bUNITS?\b", "IU", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _convert_arabic_to_english_terms(name: str) -> str:
    """Convert Arabic numerals and unit/form keywords to English equivalents."""
    text = name.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return _apply_term_replacements(text)


def _apply_term_replacements(text: str) -> str:
    replacements = {
        r"\b(?:مجم|ملجم|مليجرام|مليجرم)\b": " MG ", r"\b(?:مل|ملل|مللي|ميللي|مللتر)\b": " ML ",
        r"\b(?:جم|جرام|جرم)\b": " GM ", r"\b(?:قرص|اقراص|قراص)\b": " TAB ",
        r"\b(?:كبسول|كبسولات|كبسوله)\b": " CAP ", r"\b(?:امبول|امبولات)\b": " AMP ",
        r"\b(?:فيال|فيلات|فيالات)\b": " VIAL ", r"\b(?:نقط|قطره|قطرات)\b": " DROPS ",
        r"\b(?:بخاخ|بخاخة|سبراي)\b": " SPRAY ", r"\b(?:لبن|حليب)\b": " MILK ",
        r"\b(?:شراب|شرب)\b": " SYRUP ", r"\b(?:كريم|دهان)\b": " CREAM ",
        r"\b(?:جل|جيل)\b": " GEL ", r"\b(?:مرهم)\b": " OINTMENT ",
        r"\b(?:ايه\s+ار|اي\s+ار|ارتجاع)\b": " AR "
    }
    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def parse_drug(name: str) -> DrugComponents:
    """Parse a raw drug/product name into matching components."""
    if not name or not isinstance(name, str):
        return DrugComponents("", (), (), "", "", "", "", "", False, "", is_synthetic=False)
    
    imported = bool(_IMPORT_MARKER_RE.search(name))
    if any(0x0600 <= ord(ch) <= 0x06FF for ch in name):
        name = _convert_arabic_to_english_terms(name)
    norm = normalize(name)
    
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
    if not dosage_nums and qty and qty.isdigit() and int(qty) >= 100 and "VAGINAL" in norm_words and form in {"CAP", "SUPP"}:
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
    return DrugComponents(brand, dosage_nums, dosage_units, qty, volume, weight, form, flavor, imported, norm, variants, product_class)


def _canonical_form(word: str) -> str:
    if word in {"TABLET", "TABLETS", "TAB", "TABS"}:
        return "TAB"
    if word in {"CAP", "CAPS", "CAPSULE", "CAPSULES"}:
        return "CAP"
    if word in {"SPRAY", "SPRAYS", "DOSES", "METERED"}:
        return "SPRAY"
    if word in {"DROPS", "DROP", "OPHTALMIC", "EYE"}:
        return "EYE"
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


def _infer_missing_dosage(norm, qty, volume, weight, form):
    slash = re.search(r"\b\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?\b", norm)
    if slash:
        return (re.sub(r"\s+", "", slash.group(0)),), ("MG",)
    nums = re.findall(r"\b\d+(?:\.\d+)?\b", norm)
    consumed = [v for v in (qty, volume, weight) if v]
    remaining = []
    for num in nums:
        normalized = _canonical_number(num)
        consumed_idx = next((i for i, v in enumerate(consumed) if _canonical_number(v) == normalized), None)
        if consumed_idx is not None:
            consumed.pop(consumed_idx)
        else:
            remaining.append(normalized)
    if len(remaining) != 1:
        return (), ()
    if qty or form in {"TAB", "CAP", "SUPP", "AMP", "VIAL", "SPRAY"} or (volume and form in {"SYRUP", "SUSP"}):
        return (remaining[0],), ("MG",)
    return (), ()


def _is_brand_boundary(words, idx):
    word = words[idx]
    if word in FORM_PREFIXES or word in FORM_WORDS or word in NOISE_WORDS or word in BRAND_QUALIFIERS or _is_pediatric_inf(words, idx) or _is_descriptive_brand_word(word):
        return True
    return idx > 0 and (word in SOFT_BRAND_DESCRIPTORS or word in CONNECTOR_WORDS or word in FLAVOR_WORDS or word in SUPPLEMENT_WORDS)


def classify_product(norm):
    words = set(norm.split())
    if {"PRE", "FILLED"} <= words and "SYRINGE" in words:
        return "medicine"
    if words & DEVICE_WORDS:
        return "device"
    if words & BABY_FOOD_WORDS and not words & {"BODY", "CREAM", "LOTION"}:
        return "baby_food"
    if words & COSMETIC_WORDS:
        return "cosmetic"
    if words & SUPPLEMENT_WORDS:
        return "supplement"
    return "medicine"


def brand_variants_from_words(words, primary_brand):
    variants = []
    def add(value):
        cleaned = re.sub(r"[^A-Z0-9]", "", value)
        if len(cleaned) >= 3 and cleaned not in variants:
            variants.append(cleaned)
    add(primary_brand)
    prefix = []
    for idx, word in enumerate(words):
        if re.search(r"\d", word):
            break
        if word in FORM_PREFIXES or word in FORM_WORDS or word in NOISE_WORDS:
            break
        if _is_pediatric_inf(words, idx):
            break
        if idx > 0 and word in CONNECTOR_WORDS:
            continue
        if idx > 0 and word in BRAND_QUALIFIERS:
            break
        prefix.append(word)
        add("".join(prefix))
        if idx > 0 and word in SOFT_BRAND_DESCRIPTORS:
            break
    return tuple(variants)


def _canonical_number(value):
    return str(float(value)).rstrip("0").rstrip(".") if "." in value else value


def _weight_is_strength(weight, form, words):
    if not weight:
        return False
    if form == "TAB" and words & {"EFF", "EFFERVESCENT"}:
        return True
    return form in {"VIAL", "AMP"} or bool(words & INFUSION_CONTEXT_WORDS)


def _is_pediatric_inf(words, idx):
    if words[idx] != "INF" or idx == 0:
        return False
    return not bool(set(words) & INFUSION_CONTEXT_WORDS)


def _is_descriptive_brand_word(word):
    return word in {"GELATIN"}
