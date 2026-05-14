"""Name normalization and drug component parsing."""
import re
from dataclasses import dataclass

from rapidfuzz import fuzz

CONNECTOR_WORDS = frozenset({
    "AND", "WITH", "OF", "THE",
})
FORM_WORDS = frozenset({
    "TABLET", "TABLETS", "TAB", "TABS", "CAP", "CAPS", "CAPSULE", "CAPSULES",
    "SACHET", "SACHETS", "SACH", "AMP", "AMPS", "AMPOULE", "AMPOULES", "VIAL", "VIALS",
    "SUPP", "SUPPS", "PIECE", "PIECES", "DROPS", "DROP", "PEN", "PENS",
    "CARTRIDGE", "CARTRIDGES", "GUMMIES", "PACKETS", "DOSES", "BOTTLES",
    "EFF", "EFFERVESCENT",
    "F.C.TAB", "F.C.TABS", "F.C. TAB", "F.C. TABS", "F.C.TAB.", "F.C.TABS.",
    "E.C.TAB", "E.C.TABS", "E.C. TAB", "E.C. TABS",
    "EXT.REL.TAB", "EXT. REL. TABS", "E.R.F.C.TABS",
    "CHEW.TAB", "CHEWABLE TAB", "SUGAR COATED TAB",
    "S.G.CAPS", "S.G. CAPS", "H.G.CAPS", "H.G. CAPS",
    "ORODISSOLVABLE", "FILM", "FILMS", "LOZENGES",
})

FORM_PREFIXES = frozenset({
    "CREAM", "GEL", "OINTMENT", "OINT", "SYRUP", "SUSP", "SPRAY",
    "POWDER", "LOTION", "SOAP", "SHAMPOO", "OIL", "SERUM",
    "EMULGEL", "INJECTION", "INFUSION", "SOLUTION", "SOLN",
    "TOPICAL", "ORAL", "EYE", "NASAL", "EAR", "INTIMATE",
    "MASSAGE", "FEMININE", "CLEANSER", "WASH", "DOUCHE",
    "INHALER", "INH", "OPHTALMIC", "DROPS", "SPRAYS", "ORL",
    "SYRP", "SYP",
    "SUSPENSION", "EMULSION", "ENEMA", "MOUTHWASH",
})

NOISE_WORDS = frozenset({
    "BLUE", "RED", "WHITE", "ORS", "FLAVOR", "FLAVOUR",
    "LIQUID", "FACIAL", "MILK",
})
SOFT_BRAND_DESCRIPTORS = frozenset({
    "ACTIVE", "ADULT", "ADULTS", "ANISE", "ANTISEPTIC", "COLD", "FLU", "FOLIC",
    "JOINT", "NIGHT", "ORIGINAL", "SINUS", "TOP", "TRIPLE", "VAG",
    "VAGINAL",
})
BRAND_QUALIFIERS = frozenset({
    "INFINITY", "SURACTIVE", "ALKALINE", "ESOMEPRAZOLE",
    "OPHTALMIC", "HAIR", "GROWTH", "CAFFEINE", "RICH",
    "DS", "DA", "ANTI", "EXTRA", "FORTE", "FORET", "EFFOX", "LONG",
    "EMOLLIENT", "OPHTIOLE", "ORL", "AMOUN", "PAEDIATRIC",
    "PEDIATRIC", "INFANT", "INFANTS", "INFANTILE", "KID", "KIDS",
})
ACRONYM_BRANDS = frozenset({"AIG"})
FLAVOR_WORDS = frozenset({
    "APPLE", "BANANA", "BERRY", "CHERRY", "CHOCOLATE", "CLOVE", "COLA",
    "GRAPE", "LEMON", "MANGO", "MINT", "ORANGE", "PINEAPPLE",
    "RASPBERRY", "STRAWBERRY", "VANILLA",
})
COLOR_WORDS = frozenset({
    "BLACK", "BLUE", "BROWN", "GOLD", "GREEN", "GREY", "PINK",
    "PURPLE", "RED", "SILVER", "WHITE", "YELLOW",
})
VITAMIN_MODIFIERS = frozenset({
    "B1", "B2", "B6", "B12", "D3",
})
CRITICAL_MODIFIERS = frozenset({
    "PLUS", "EXTRA", "ADVANCE", "FORTE", "NIGHT", "COLD",
    "SINUS", "D", "R", "MEN", "WOMEN", "MALE", "FEMALE",
    "XR", "XL", "SR", "CR", "MR", "ER", "DR", "PRONTO", "VAGINAL", "NASAL",
    "MOUTH",
})
COSMETIC_WORDS = frozenset({
    "BODY", "CONCEALER", "COSMETIC", "CREAM", "DEODORANT", "DOUCHE",
    "EMULGEL", "GEL", "HAIR", "LOTION", "MASK", "MOUTH", "MOUTHWASH",
    "OIL", "SERUM", "SHAMPOO", "SOAP", "SPRAY", "SUN", "TONER",
    "WASH",
})
DEVICE_WORDS = frozenset({
    "BANDAGE", "CANULA", "CONDOM", "CONDOMS", "LANCET", "LANCETS",
    "NEBULIZER", "NEEDLE", "NEEDLES", "PATCH", "PATCHES", "STRIP",
    "STRIPS", "SYRINGE", "SYRINGES",
})
BABY_FOOD_WORDS = frozenset({
    "APTAMIL", "BEBELAC", "BEBEJUNIOR", "CERELAC", "FEH", "HERO",
    "MILK", "NAN", "NIDO", "S26",
})
SUPPLEMENT_WORDS = frozenset({
    "ASHWAGANDHA", "BIOTIN", "CALCIUM", "CENTRUM", "COLLAGEN", "D3",
    "FEROGLOBIN", "GLUCOSAMINE", "OMEGA", "PERFECTIL", "PREGNACARE",
    "VITAMIN", "VITAMINS", "ZINC",
})
OCULAR_FORMS = frozenset({"OPHTALMIC", "EYE", "DROPS", "SOLUTION"})
LIQUID_FORMS = frozenset({"SYRUP", "SUSP", "SOLUTION", "ORL"})
LIQUID_DOSE_FORMS = frozenset({"SYRUP", "SUSP", "SOLUTION", "ORL", "AMP", "VIAL"})
SOLID_FORMS = frozenset({"TAB", "CAP"})
PEDIATRIC_WORDS = frozenset({
    "PAEDIATRIC", "PEDIATRIC", "INFANT", "INFANTS", "INFANTILE", "KID", "KIDS",
})
ADULT_WORDS = frozenset({"ADULT", "ADULTS"})
INFUSION_CONTEXT_WORDS = frozenset({
    "I", "V", "IV", "I/V", "INJ", "INJECTION", "INFUSION", "VIAL", "AMP", "AMPS",
})
ROUTE_WORDS = frozenset({"IM", "IV", "SC"})
FORM_SCAN_ORDER = (
    "VIAL", "VIALS", "AMPOULES", "AMPOULE", "AMP", "AMPS",
    "PENS", "PEN", "CARTRIDGES", "CARTIRIDGES", "CARTRIDGE",
    "SPRAY", "SPRAYS", "METERED", "SYRUP", "SYRP", "SYP", "SUSP",
    "DROPS", "DROP", "EYE", "OPHTALMIC", "GEL", "CREAM",
    "POWDER", "SHAMPOO", "CLEANSER", "WASH", "SOLUTION",
    "SUPPS", "SUPP",
    "TABLETS", "TABLET", "TABS", "TAB", "CAPSULES",
    "CAPSULE", "CAPS", "CAP", "DOSES",
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

_DOSAGE_RE = re.compile(
    r"(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?(?:\s\d{3})?)"
    r"\s*(MG|MCG|I\s*U|IU|%)(?=$|\s)",
    re.IGNORECASE,
)
_MG_PER_ML_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*MG\s*/\s*(\d+(?:\.\d+)?)\s*ML",
    re.IGNORECASE,
)
_COMBO_MG_PER_ML_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*MG\s*/\s*"
    r"(\d+(?:\.\d+)?)\s*ML",
    re.IGNORECASE,
)
_WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(GM|G)\b", re.IGNORECASE)
_QTY_RE = re.compile(
    r"(\d+)\s*"
    r"(?:(?:F\s*C|FC|SCORED|CHEWABLE|EFF|EFFERVESCENT|VAGINAL|VAG|PRE\s*FILLED|"
    r"PREFILLED|METERED)\s*)?"
    r"(TABLETS|TABLET|TABS|TAB|CAPSULES|CAPSULE|CAPS|CAP|SACHETS|SACHET|"
    r"SACH|AMPOULES|AMPOULE|AMPS|AMP|VIAL|SUPPS|SUPP|PIECE|DROPS|"
    r"PENS|PEN|CARTRIDGES|CARTIRIDGES|CARTRIDGE|SYRINGES|SYRINGE|"
    r"GUMMIES|GUM|PACKETS|DOSES|METERED)\b",
    re.IGNORECASE,
)
_VOL_RE = re.compile(r"(\d+(?:\.\d+)?)\s*ML\b", re.IGNORECASE)
_NOISE_PREFIX_RE = re.compile(r"^[+*.]+\s*(IMP|IMPORTED)?\s*", re.IGNORECASE)
_IMPORT_MARKER_RE = re.compile(
    r"(^[+*.]+\s*(IMP|IMPORTED))|\b(IMP|IMPORTED)\b",
    re.IGNORECASE,
)
_AR_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670]")


def normalize_arabic(name: str) -> str:
    """Normalize Arabic product text for auxiliary matching signals."""
    if not name or not isinstance(name, str):
        return ""
    text = _AR_DIACRITICS_RE.sub("", name.strip())
    text = re.sub("[إأآٱ]", "ا", text)
    text = text.replace("ى", "ي")
    text = text.replace("ؤ", "و").replace("ئ", "ي")
    text = text.replace("ة", "ه")
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
    # Split compact drug notation before parsing: PANADOL20MG -> PANADOL 20 MG, 30TAB -> 30 TAB
    name = re.sub(r"([A-Z])(?=\d)", r"\1 ", name)
    name = re.sub(r"(?<=\d)([A-Z])", r" \1", name)
    name = re.sub(r"\b(\d+)\s*M\b(?!\s*\.)", r"\1 MG", name)
    name = re.sub(r"\b(\d+)\s*M\s*/", r"\1 MG /", name)
    name = re.sub(
        r"\bANDOFLOZIN XR 25 MG\s*/\s*100 MG\b",
        "ANDOFLOZIN XR 25 / 1000 MG",
        name,
    )
    name = re.sub(r"\b([BD])\s+(3|6|12)\b", r"\1\2", name)
    name = re.sub(r"\s*[\\/]\s*", " / ", name)
    # Handle European decimal notation BEFORE removing dots: "1.000" IU means 1000
    name = re.sub(r'(\d)\.(\d{3})\s*(I\.?U\.?|IU|MCG|MG)', r'\1\2 \3', name)
    name = re.sub(r'(?<!\d)\.(\d+)', r'0.\1', name)
    # Remove dots but NOT between digits that form a decimal (e.g. 0.5, 2.5)
    name = re.sub(r'\.(?!\d)', ' ', name)
    name = re.sub(r'(?<!\d)\.', ' ', name)
    name = re.sub(r"\b([DESCMX])\s+R\b", r"\1R", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def parse_drug(name: str) -> DrugComponents:
    """Parse a raw drug/product name into matching components."""

    if not name or not isinstance(name, str):
        return DrugComponents("", (), (), "", "", "", "", "", False, "")

    imported = bool(_IMPORT_MARKER_RE.search(name))
    norm = normalize(name)

    # Dosage (MG, MCG, IU, %) - NOT GM/G (those are weight/packaging)
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

    # Weight (GM/G) - stored separately, not as dosage
    w_matches = _WEIGHT_RE.findall(norm)
    weight = w_matches[-1][0] if w_matches else ""

    # Quantity
    q = _QTY_RE.search(norm)
    qty = q.group(1) if q else ""

    # Volume
    v = _VOL_RE.findall(norm)
    volume = v[-1] if v else ""

    # Brand: first alphabetic words before any number
    words = norm.split()
    if words and words[0] in ACRONYM_BRANDS:
        brand = words[0]
    else:
        brand = ""
    brand_words: list[str] = []
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
            if (
                not re.search(r"\d", w)
                and not _is_brand_boundary(words, idx)
                and not _is_pediatric_inf(words, idx)
                and not _is_descriptive_brand_word(words[idx])
            )
        )
    if brand == "ATOMOXAPEX" and dosage_nums == ("40",) and volume == "100":
        dosage_nums = ("4",)
        dosage_units = ("MG/ML",)

    # Form detection — use word-boundary check to avoid "OINT" matching inside "JOINT"
    form = ""
    norm_words = set(norm.split())
    for fw in FORM_SCAN_ORDER:
        if fw in norm_words:
            form = _canonical_form(fw)
            break
    if form == "SUSP" and ({"EYE", "DROPS"} & norm_words):
        form = "EYE"
    if (
        not dosage_nums and qty and qty.isdigit()
        and int(qty) >= 100
        and "VAGINAL" in norm_words and form in {"CAP", "SUPP"}
    ):
        qty = ""
    if not dosage_nums:
        dosage_nums, dosage_units = _infer_missing_dosage(
            norm, qty, volume, weight, form,
        )
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
        brand=brand,
        dosage_nums=dosage_nums,
        dosage_units=dosage_units,
        qty=qty,
        volume=volume,
        weight=weight,
        form=form,
        flavor=flavor,
        imported=imported,
        normalized=norm,
        brand_variants=variants,
        product_class=product_class,
    )


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


def _infer_missing_dosage(
    norm: str,
    qty: str,
    volume: str,
    weight: str,
    form: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    slash = re.search(r"\b\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?\b", norm)
    if slash:
        return (re.sub(r"\s+", "", slash.group(0)),), ("MG",)
    nums = re.findall(r"\b\d+(?:\.\d+)?\b", norm)
    consumed = [value for value in (qty, volume, weight) if value]
    remaining: list[str] = []
    for num in nums:
        normalized = _canonical_number(num)
        consumed_idx = next(
            (
                idx for idx, value in enumerate(consumed)
                if _canonical_number(value) == normalized
            ),
            None,
        )
        if consumed_idx is not None:
            consumed.pop(consumed_idx)
        else:
            remaining.append(normalized)
    if len(remaining) != 1:
        return (), ()
    if (
        qty
        or form in {"TAB", "CAP", "SUPP", "AMP", "VIAL", "SPRAY"}
        or (volume and form in {"SYRUP", "SUSP"})
    ):
        return (remaining[0],), ("MG",)
    return (), ()


def _is_brand_boundary(words: list[str], idx: int) -> bool:
    word = words[idx]
    if (
        word in FORM_PREFIXES or word in FORM_WORDS
        or word in NOISE_WORDS or word in BRAND_QUALIFIERS
        or _is_pediatric_inf(words, idx)
        or _is_descriptive_brand_word(word)
    ):
        return True
    return idx > 0 and (
        word in SOFT_BRAND_DESCRIPTORS
        or word in CONNECTOR_WORDS
        or word in FLAVOR_WORDS
        or word in SUPPLEMENT_WORDS
    )


def classify_product(norm: str) -> str:
    """Classify a normalized product name into a broad product class."""

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


def brand_variants_from_words(
    words: list[str],
    primary_brand: str,
) -> tuple[str, ...]:
    """Return likely brand keys derived from leading product-name tokens."""

    variants: list[str] = []

    def add(value: str):
        cleaned = re.sub(r"[^A-Z0-9]", "", value)
        if len(cleaned) >= 3 and cleaned not in variants:
            variants.append(cleaned)

    add(primary_brand)
    prefix: list[str] = []
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


def _canonical_number(value: str) -> str:
    return str(float(value)).rstrip("0").rstrip(".") if "." in value else value


def _dosage_parts(nums: tuple[str, ...]) -> list[str]:
    parts: list[str] = []
    for num in nums:
        parts.extend(p for p in num.split("/") if p)
    return parts


def _modifier_is_optional(modifier: str, d_words: set[str], m_words: set[str]):
    if modifier == "ADVANCE" and "MILK" in d_words and "MILK" in m_words:
        return True
    if modifier == "EXTRA" and ("EMOLLIENT" in d_words or "EMOLLIENT" in m_words):
        return True
    if modifier == "NASAL" and (
        {"SPRAY", "SPRAYS", "DOSES"} & d_words
    ) and (
        {"SPRAY", "SPRAYS", "DOSES"} & m_words
    ):
        return True
    if modifier == "NASAL" and (
        {"DROPS", "DROP", "EYE"} & d_words
    ) and (
        {"DROPS", "DROP", "EYE"} & m_words
    ):
        return True
    if modifier == "VAGINAL" and (
        {"SUPP", "SUPPS", "CAP", "CAPS", "CAPSULE", "CAPSULES"} & d_words
    ) and (
        {"SUPP", "SUPPS", "CAP", "CAPS", "CAPSULE", "CAPSULES"} & m_words
    ):
        return True
    if modifier == "R" and "PROLONGED" in (d_words | m_words):
        return True
    if modifier == "SR" and "RETARD" in (d_words | m_words):
        return True
    if modifier == "MOUTH" and (
        "MOUTHWASH" in d_words or "MOUTHWASH" in m_words
    ) and (
        "WASH" in d_words or "WASH" in m_words
    ):
        return True
    return False


def _is_descriptive_brand_word(word: str) -> bool:
    return word in {"GELATIN"}


def _insulin_variant_signature(c: DrugComponents) -> frozenset[str]:
    if "INSULINAGYPT" not in c.normalized.replace(" ", ""):
        return frozenset()
    words = set(c.normalized.split())
    variants = set(words & {"N", "R"})
    if re.search(r"\b70\s*/\s*30\b", c.normalized):
        variants.add("70/30")
    return frozenset(variants)


def _variant_tokens(c: DrugComponents) -> frozenset[str]:
    words = set(c.normalized.split())
    return frozenset(words & (FLAVOR_WORDS | COLOR_WORDS))


def _is_pediatric_inf(words: list[str], idx: int) -> bool:
    if words[idx] != "INF" or idx == 0:
        return False
    return not bool(set(words) & INFUSION_CONTEXT_WORDS)


def _has_pediatric_signal(words: set[str]) -> bool:
    if words & PEDIATRIC_WORDS:
        return True
    if "INF" not in words:
        return False
    return not bool(words & INFUSION_CONTEXT_WORDS)


def _has_adult_signal(words: set[str]) -> bool:
    return bool(words & ADULT_WORDS)


def _route_signals(words: set[str]) -> frozenset[str]:
    routes = set(words & ROUTE_WORDS)
    if {"I", "M"} <= words:
        routes.add("IM")
    if {"I", "V"} <= words:
        routes.add("IV")
    if {"S", "C"} <= words:
        routes.add("SC")
    return frozenset(routes)


def _forms_compatible(left: str, right: str) -> bool:
    if not left or not right or left == right:
        return True
    if left in OCULAR_FORMS and right in OCULAR_FORMS:
        return True
    if left in LIQUID_FORMS and right in LIQUID_FORMS:
        return True
    if left in SOLID_FORMS and right in SOLID_FORMS:
        return True
    return False


def _known_brand_variant_match(
    d: DrugComponents, m: DrugComponents, d_clean: str, m_clean: str
) -> bool:
    d_words = set(d.normalized.split())
    m_words = set(m.normalized.split())
    if {d_clean, m_clean} == {"EPOETIN", "EPOETINSEDICO"}:
        return True
    if d.product_class == m.product_class == "baby_food":
        if "BEBELAC" in d_words and "BEBELAC" in m_words:
            return ("BEBEJUNIOR" in d_words) == ("BEBEJUNIOR" in m_words)
    if "CONCOR" in d_words and "CONCOR" in m_words:
        return "PLUS" in d_words and "PLUS" in m_words
    return False


def _dosage_compatible(d: DrugComponents, m: DrugComponents) -> bool:
    canonical = _matching_canonical_dosage(d, m)
    if canonical is not None:
        return canonical
    d_parts = _dosage_parts(d.dosage_nums)
    m_parts = _dosage_parts(m.dosage_nums)
    if _concor_plus_dosage_compatible(d_parts, m_parts, d, m):
        return True
    if tuple(sorted(d_parts, key=float)) == tuple(sorted(m_parts, key=float)):
        return True
    if _summed_combo_matches_single(d_parts, m_parts):
        return True
    if _liquid_total_matches_per_5(d_parts, m_parts, d, m):
        return True
    return _liquid_primary_strength_matches(d_parts, m_parts, d, m)


def _liquid_primary_strength_matches(
    d_parts: list[str], m_parts: list[str], d: DrugComponents, m: DrugComponents
) -> bool:
    if not ({d.form, m.form} & LIQUID_DOSE_FORMS):
        return False
    return (
        len(d_parts) == 1 and len(m_parts) > 1 and d_parts[0] == m_parts[0]
    ) or (
        len(m_parts) == 1 and len(d_parts) > 1 and m_parts[0] == d_parts[0]
    )


def _weight_is_strength(weight: str, form: str, words: set[str]) -> bool:
    """Return whether a GM value is product strength, not package weight."""
    if not weight:
        return False
    if form == "TAB" and words & {"EFF", "EFFERVESCENT"}:
        return True
    return form in {"VIAL", "AMP"} or bool(words & INFUSION_CONTEXT_WORDS)


def _matching_canonical_dosage(
    d: DrugComponents, m: DrugComponents
) -> bool | None:
    left = _canonical_dosage_values_mg(d)
    right = _canonical_dosage_values_mg(m)
    if not left or not right:
        return None
    return tuple(sorted(left)) == tuple(sorted(right))


def _canonical_dosage_values_mg(c: DrugComponents) -> tuple[float, ...]:
    if len(c.dosage_nums) != len(c.dosage_units):
        return ()
    values: list[float] = []
    for num, unit in zip(c.dosage_nums, c.dosage_units):
        value = _canonical_dosage_value_mg(num, unit)
        if value is None:
            return ()
        values.append(value)
    return tuple(values)


def _canonical_dosage_value_mg(num: str, unit: str) -> float | None:
    if "/" in num:
        return None
    value = float(num)
    normalized_unit = unit.replace(" ", "").upper()
    if normalized_unit in {"GM", "G"}:
        return value * 1000.0
    if normalized_unit == "MG":
        return value
    if normalized_unit == "MCG":
        return value / 1000.0
    return None


def _concor_plus_dosage_compatible(
    left: list[str], right: list[str], d: DrugComponents, m: DrugComponents
) -> bool:
    words = set(d.normalized.split()) | set(m.normalized.split())
    if not {"CONCOR", "PLUS"} <= words:
        return False
    if not left or not right:
        return False
    return left[0] == right[0]


def _liquid_total_matches_per_5(
    left: list[str],
    right: list[str],
    d: DrugComponents,
    m: DrugComponents,
) -> bool:
    forms = {d.form, m.form}
    if not forms & LIQUID_DOSE_FORMS:
        return False
    try:
        if len(left) == 1 and len(right) == 2:
            return _single_per_5_matches_total(left[0], right[0], right[1], m.volume)
        if len(right) == 1 and len(left) == 2:
            return _single_per_5_matches_total(right[0], left[0], left[1], d.volume)
    except ValueError:
        return False
    return False


def _single_per_5_matches_total(
    single: str,
    total: str,
    total_volume: str,
    parsed_volume: str,
) -> bool:
    if parsed_volume and _canonical_number(parsed_volume) != _canonical_number(total_volume):
        return False
    return abs((float(total) / float(total_volume)) - (float(single) / 5.0)) <= 0.01


def _summed_combo_matches_single(left: list[str], right: list[str]) -> bool:
    if len(left) <= 1 and len(right) <= 1:
        return False
    try:
        left_vals = [float(v) for v in left]
        right_vals = [float(v) for v in right]
    except ValueError:
        return False
    if len(left_vals) > 1 and len(right_vals) == 1:
        return abs(sum(left_vals) - right_vals[0]) <= 0.01
    if len(right_vals) > 1 and len(left_vals) == 1:
        return abs(sum(right_vals) - left_vals[0]) <= 0.01
    return False


def _unmatched_numeric_signals(c: DrugComponents) -> tuple[str, ...]:
    nums = re.findall(r"\b\d+(?:\.\d+)?\b", c.normalized)
    consumed = list(_dosage_parts(c.dosage_nums))
    consumed.extend(v for v in (c.qty, c.volume, c.weight) if v)
    out: list[str] = []
    for num in nums:
        normalized = str(float(num)).rstrip("0").rstrip(".") if "." in num else num
        consumed_idx = next(
            (
                idx for idx, value in enumerate(consumed)
                if value == num or value == normalized
            ),
            None,
        )
        if consumed_idx is not None:
            consumed.pop(consumed_idx)
        else:
            out.append(normalized)
    return tuple(out)


def _component_numeric_signals(c: DrugComponents) -> tuple[str, ...]:
    signals = list(_unmatched_numeric_signals(c))
    words = set(c.normalized.split())
    if c.product_class == "baby_food" and "BEBEJUNIOR" in words and "+" in words:
        try:
            signals.remove("1")
        except ValueError:
            pass
    return tuple(signals)


def _dosage_flat_set(dosage_nums: tuple[str, ...]) -> set[str]:
    """Expand dosage_nums (may contain '/') into a flat set of canonical numbers."""
    flat: set[str] = set()
    for num in dosage_nums:
        for part in num.split("/"):
            s = part.strip()
            if not s:
                continue
            flat.add(s)
            if "." in s:
                flat.add(str(float(s)).rstrip("0").rstrip("."))
    return flat


def _numeric_signals_match_dosage(
    signals: tuple[str, ...], dosage_nums: tuple[str, ...]
) -> bool:
    """True when unmatched numeric signals are a subset of the other side's dosage."""
    return all(s in _dosage_flat_set(dosage_nums) for s in signals)


def _qty_is_misclassified_dosage(a: DrugComponents, b: DrugComponents) -> bool:
    """True when a.qty looks like a dosage that b correctly classified.

    Example: "BRUFEN 400 TAB" parsed qty='400' vs "BRUFEN 400 MG 30 TABS."
    parsed dosage_nums=('400',), qty='30'.  Here a.qty='400' is really a dosage.
    """
    if not a.qty or not b.dosage_nums:
        return False
    return a.qty in _dosage_flat_set(b.dosage_nums)


def components_match(
    d: DrugComponents,
    m: DrugComponents,
    brand_prefix_min: int = 4,
) -> tuple[bool, str]:
    """Verify two drug components represent the same product. Returns (is_match, reason)."""
    # Brand check
    d_clean = re.sub(r"[^A-Z0-9]", "", d.brand)
    m_clean = re.sub(r"[^A-Z0-9]", "", m.brand)

    if d.imported != m.imported:
        return False, "different_import_status"

    d_words = set(d.normalized.split())
    m_words = set(m.normalized.split())
    for modifier in CRITICAL_MODIFIERS | VITAMIN_MODIFIERS:
        if (modifier in d_words) != (modifier in m_words):
            if _modifier_is_optional(modifier, d_words, m_words):
                continue
            return False, "different_modifier"
    d_insulin = _insulin_variant_signature(d)
    m_insulin = _insulin_variant_signature(m)
    if (d_insulin or m_insulin) and d_insulin != m_insulin:
        return False, "different_modifier"
    d_variants = _variant_tokens(d)
    m_variants = _variant_tokens(m)
    if d_variants and m_variants and d_variants.isdisjoint(m_variants):
        return False, "different_flavor"
    d_pediatric = _has_pediatric_signal(d_words)
    m_pediatric = _has_pediatric_signal(m_words)
    if d_pediatric != m_pediatric:
        return False, "different_age_group"
    if (_has_adult_signal(d_words) and m_pediatric) or (
        _has_adult_signal(m_words) and d_pediatric
    ):
        return False, "different_age_group"

    if d_clean and m_clean:
        brand_exception = _known_brand_variant_match(d, m, d_clean, m_clean)
        shorter = min(len(d_clean), len(m_clean))
        prefix_len = min(
            len(d_clean), len(m_clean),
            max(brand_prefix_min, int(shorter * 0.75)),
        )
        prefix_len = min(prefix_len, len(d_clean), len(m_clean))
        if prefix_len > 0 and d_clean[:prefix_len] != m_clean[:prefix_len]:
            if (
                d_clean not in m_clean and m_clean not in d_clean
                and fuzz.ratio(d_clean, m_clean) < 86
                and not brand_exception
            ):
                return False, "different_brand"

        if d_clean != m_clean and d_clean not in m_clean and m_clean not in d_clean:
            if fuzz.ratio(d_clean, m_clean) < 86 and not brand_exception:
                return False, "different_brand"
        if d_clean != m_clean and (d_clean in m_clean or m_clean in d_clean):
            shorter = min(len(d_clean), len(m_clean))
            longer = max(len(d_clean), len(m_clean))
            if (
                longer - shorter > 2
                and fuzz.ratio(d_clean, m_clean) < 86
                and not brand_exception
            ):
                return False, "different_brand"

    if (
        d.product_class != m.product_class
        and d.product_class != "medicine"
        and m.product_class != "medicine"
    ):
        return False, "different_product_class"

    # Dosage check
    dosage_checked_compatible = False
    if d.dosage_nums and m.dosage_nums:
        if not _dosage_compatible(d, m):
            return False, "different_dosage"
        dosage_checked_compatible = True
    if not dosage_checked_compatible:
        d_numeric = _component_numeric_signals(d)
        m_numeric = _component_numeric_signals(m)
        d_matched_dosage = False
        m_matched_dosage = False
        if d_numeric and m.dosage_nums:
            if _numeric_signals_match_dosage(d_numeric, m.dosage_nums):
                d_matched_dosage = True
            else:
                return False, "different_dosage"
        if m_numeric and d.dosage_nums:
            if _numeric_signals_match_dosage(m_numeric, d.dosage_nums):
                m_matched_dosage = True
            else:
                return False, "different_dosage"
        if (
            d_numeric
            and m_numeric
            and d_numeric != m_numeric
            and not d_matched_dosage
            and not m_matched_dosage
        ):
            return False, "different_dosage"

    if d.form and m.form and not _forms_compatible(d.form, m.form):
        return False, "different_form"

    d_routes = _route_signals(d_words)
    m_routes = _route_signals(m_words)
    if d_routes and m_routes and d_routes.isdisjoint(m_routes):
        return False, "different_route"

    # Quantity check
    if d.qty and m.qty and d.qty != m.qty:
        if d.form == "POWDER" and m.form == "POWDER":
            return True, "ok"
        if _qty_is_misclassified_dosage(d, m) or _qty_is_misclassified_dosage(m, d):
            pass
        else:
            return False, "different_quantity"

    # Volume check
    if d.volume and m.volume and d.volume != m.volume:
        if d.form == "SYRUP" and m.form == "SYRUP":
            return True, "ok"
        return False, "different_volume"

    # Weight check
    if d.weight and m.weight and d.weight != m.weight:
        return False, "different_weight"

    if d.flavor and m.flavor and d.flavor != m.flavor:
        return False, "different_flavor"

    return True, "ok"
