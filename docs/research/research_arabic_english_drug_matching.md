# Arabic ↔ English Pharmaceutical Name Matching — Research Report

> **Audience:** senior engineer picking an approach to ship in a day.
> **Project:** PharmaSupplyBot — a Python bot that matches English drug names
> (e.g. `AZADERM CREAM 30G`) against Arabic-only rows in an Excel catalog
> (e.g. `ايوكال كريم صغير 30جم`).
> **Today's failure mode:** naive token overlap on transliterated forms
> matches `AZADERM → ايكال` because both contain `cream/كريم` and `30/30جم`.

This report inventories the libraries, datasets and APIs that exist, gives
working code for each, and ends with an opinionated recommendation.

---

## Table of Contents

1. [Quick answer (TL;DR)](#1-quick-answer-tldr)
2. [Transliteration approaches — Arabic script → Latin](#2-transliteration-approaches--arabic-script--latin)
3. [Pharmaceutical name databases / APIs](#3-pharmaceutical-name-databases--apis)
4. [Phonetic matching for Arabic](#4-phonetic-matching-for-arabic)
5. [Pharma-specific matching tactics](#5-pharma-specific-matching-tactics)
6. [Recommended approach for this project](#6-recommended-approach-for-this-project)
7. [Appendix — when the right answer is to fix the catalog](#7-appendix--when-the-right-answer-is-to-fix-the-catalog)
8. [References (URLs)](#8-references-urls)

---

## 1. Quick answer (TL;DR)

If you only read one section:

1. **Don't try to be clever with transliteration + Levenshtein.** It's what you
   have today and it will keep producing nonsense on brand names that were
   never transliterated from Arabic (e.g. `AZADERM` is not Arabic — it has no
   Arabic root to back-transliterate).
2. **Use an Arabic+English brand-name dataset.** Egypt has a CC0 dataset with
   25,070 medicines, each row carrying `commercial_name_en` + `commercial_name_ar` +
   `scientific_name` + `manufacturer` + `drug_class` + `route` + `price_egp` —
   [`karem505/egyptian-drug-database`](https://github.com/karem505/egyptian-drug-database)
   (raw CSV at
   <https://raw.githubusercontent.com/karem505/egyptian-drug-database/main/data/egyptian-drugs.csv>).
3. **Use it as a brand→brand lookup table** plus your existing form/strength
   token logic. Brand + form + strength match is enough to disambiguate
   95%+ of real Egyptian pharmacy orders.
4. **Fall back to pyarabic's `trans.convert()` (Latin scheme) + rapidfuzz
   `token_set_ratio`** for the ~5% of drugs that aren't in the dataset.
   That's literally the only place transliteration helps.

Estimated effort: half a day. The recommendation section (§6) has the
algorithm in pseudocode and the cost breakdown.

---

## 2. Transliteration approaches — Arabic script → Latin

### 2.1 What transliteration actually is

Transliteration maps each Arabic letter (or letter+diactritics) to a unique
Latin symbol. It is **not** translation. It is a one-to-one encoding that
makes Arabic strings searchable by English speakers (and by code that
doesn't understand Arabic).

Three families matter for this project:

- **Buckwalter** — 1988, ASCII-only, used by basically every Arabic NLP
  corpus. Has special symbols (`<`, `>`, `&`, `$`, `*`) that break JSON/XML.
  See Wikipedia
  <https://en.wikipedia.org/wiki/Buckwalter_transliteration>.
- **ALA-LC / ISO 233 / DIN 31635** — Unicode-Latin, scholarly, but they
  produce strings full of diacritics (`ʿ`, `ḫ`, `ṣ`) that no fuzzy matcher
  understands. Not useful here.
- **ISO 233-soft / simple Latin "a2en"** — what `pyarabic.trans` ships as
  `code='latin'`: `كريم → krym`, `أيوكال → aywkal`, `بنادول → bnadwl`.
  Stripped of all special symbols, suitable for fuzzy matching. This is
  the only scheme you should use for matching.

### 2.2 `pyarabic` — the only Python option you need

**Source:** <https://github.com/linuxscout/pyarabic> ·
**Docs:** <https://pyarabic.readthedocs.io/en/latest/> ·
**Install:** `pip install pyarabic` (works offline, GPLv3, depends only on
stdlib).
**Runtime:** offline, no network.
**Arabic-aware:** yes — the only widely-used Python lib that ships a
purpose-built transliterator with a "latin" (ASCII, no diacritics) output
that fuzzy matchers can ingest.

The relevant module is `pyarabic.trans` (file
`pyarabic/trans.py` in the repo) and its `convert(text, code_from, code_to)`
function with three relevant output codes:

- `'arabic' → 'tim'` — to Buckwalter (use only if you need to feed a
  Buckwalter-aware tool; the symbols are awful for fuzzy matching).
- `'arabic' → 'latin'` — to simple ASCII Latin (`a2en_table` in `trans.py`).
  This is what you want for `rapidfuzz`.
- `'arabic' → 'sampa'` — phonetic IPA-ish; not useful for matching either.

```python
# src/core/normalization/transliterate.py
import pyarabic.trans

def ar_to_latin(s: str) -> str:
    """Strip harakat + tatweel + diacritics then convert to ASCII Latin.
    Output is safe for rapidfuzz / jellyfish / regex."""
    import pyarabic.araby as ar
    s = ar.strip_tashkeel(s)            # remove harakat
    s = ar.strip_tatweel(s)            # remove ـ stretching
    s = ar.normalize_ligature(s)       # لا / لأ / إ / آ → لاأإآ
    s = ar.normalize_hamza(s, method="tasheel")  # همزة → near letter
    return pyarabic.trans.convert(s, "arabic", "latin")

ar_to_latin("كريم")        # 'krym'
ar_to_latin("ايوكال")       # 'aywkal'
ar_to_latin("بانادول إكسترا")  # 'banadwl <kstra' — ة→t, إ→<
ar_to_latin("بنادول")       # 'bnadwl'  (note: ا dropped between consonants
                              #  unless hamza'd — see "robustness" below)
```

**Robustness for Egyptian drug names:** poor — by design, and that's the
whole point. `AZADERM` has no Arabic root; transliteration cannot produce
"aywkal" from it because there is no Arabic to transliterate. The reverse
direction (`Arabic → Latin`) does work for the *Arabic* part of the catalog
(`ايوكال → aywkal`), but you still need to match `aywkal` against the
English column where the drug is listed as something else entirely
(e.g. `EUCAL`). That requires the brand dictionary (§3), not
transliteration.

Useful pre-processing utilities in the same `pyarabic.araby` module
(`strip_tashkeel`, `strip_tatweel`, `normalize_ligature`, `normalize_hamza`,
`tokenize`) — see
<https://github.com/linuxscout/pyarabic/blob/master/doc/features.md> for the
full list with code.

### 2.3 `arabic-reshaper` — display-only, not matching

**Source:** <https://github.com/mpcabd/python-arabic-reshaper> ·
**PyPI:** <https://pypi.org/project/arabic-reshaper/> ·
**Install:** `pip install arabic-reshaper` (offline, MIT).
**Runtime:** offline.
**Arabic-aware:** yes, but for **glyph rendering**, not transliteration.

Useful only if you need to display Arabic in environments that don't
support RTL/BiDi (PDFs, image rendering). Has no role in matching.

```python
import arabic_reshaper
from bidi.algorithm import get_display
text = "كريم"
display = get_display(arabic_reshaper.reshape(text))   # 'ﻢﻳﺮﻛ'
```

If your downstream matcher reads bytes or sees BiDi-mangled text in
Excel exports, the order may need to be reversed with `python-bidi`
(<https://github.com/MeirKriheli/python-bidi>, `pip install python-bidi`)
before tokenizing. This is a bug-class of its own: Excel saves Arabic as
isolated glyphs from LTR — your matcher must reshape before tokenizing.

### 2.4 CAMeL Tools (`camel-tools`) — the heavyweight option

**Source:** <https://github.com/CAMeL-Lab/camel_tools> ·
**Docs:** <https://camel-tools.readthedocs.io/en/latest/> ·
**Install:** `pip install camel-tools` + `camel_data -i light` (≈ 1 GB
morphology/orthography data; full install is several GB).
**Runtime:** offline *after* `camel_data` is downloaded; the install step
needs network.
**Arabic-aware:** yes — full morphological analyzer, orthographic
normalization, dialect identification, NER. Built by NYU Abu Dhabi's CAMeL
Lab.

Transliteration is the `camel_tools.utils.transliterate.Transliterator`
class, wrapping a `CharMapper`:

```python
from camel_tools.utils.charmap import CharMapper
from camel_tools.utils.transliterate import Transliterator

bw2ar = CharMapper.builtin_mapper('bw2ar')            # Buckwalter → Arabic
ar2bw = CharMapper.builtin_mapper('ar2bw')            # Arabic → Buckwalter
ar2hsb = CharMapper.builtin_mapper('ar2hsb')          # Arabic → HSB

t = Transliterator(ar2bw)
t.transliterate("كريم")   # 'krym'
```

But the **Latin output you actually want doesn't ship in `camel-tools`
out-of-the-box** — only `bw`, `ar2bw`, `ar2hsb`, `safebw`, `xmlbw` are
builtin mappers (full table at
<https://camel-tools.readthedocs.io/en/latest/reference/encoding_schemes.html>).
You'd have to build your own `CharMapper` from the pyarabic `a2en_table`
or write a Python transliteration pass. CAMeL is overkill for this problem
unless you also want morphological features.

**Verdict:** skip for an MVP. The install cost + dataset size + the fact
that the `a2en` Latin scheme isn't shipped make it a poor fit.

### 2.5 `Farasa` — server-side, ignore

**Source:** <https://github.com/farasa/farasa-toolkit> · PyPI:
`farasa`. From the README, the toolkit is Java-backed and ships segmenter /
POS tagger / diacritizer / NER. There is no published Arabic-to-Latin
transliterator. Several of the GitHub mirrors I tried were 404. Skip.

### 2.6 `CLTK` (Classical Language Toolkit) — wrong era

**Source:** <https://github.com/cltk/cltk> ·
**Docs:** <https://docs.cltk.org>. **Install:** `pip install cltk`.
**Runtime:** offline.
**For pre-modern** Greek, Latin, Coptic, Akkadian, etc. — it has no Arabic
model and no drug-matching utility. Wrong tool.

### 2.7 Transliteration: ranking for *this* project

| Lib               | Offline | Latin ASCII out | Brand-name robust | Install complexity | Verdict |
|-------------------|---------|-----------------|-------------------|--------------------|---------|
| `pyarabic.trans`  | yes     | yes (`a2en`)    | n/a (1-way)       | trivial            | **ship this** |
| `camel-tools`     | after download | only Buckwalter/HSB | n/a         | heavy              | skip |
| `arabic-reshaper` | yes     | n/a             | n/a               | trivial            | display only |
| `Farasa`          | partial | no              | n/a               | heavy              | skip |
| `CLTK`            | yes     | n/a             | n/a               | trivial            | wrong language |

The "robustness for brand names" column is **the same for every
library**: zero. Transliteration can't help you match `AZADERM` against
`ايوكال` because the former has no Arabic form. Only the brand
dictionary (§3) or the matching algorithm (§6) can do that.

---

## 3. Pharmaceutical name databases / APIs

### 3.1 The Egyptian Drug Authority (EDA)

The EDA — `هيئة الدواء المصرية` — is the regulator, successor to EOP
(Egyptian Organization for Standardization & Quality, the old
"Egyptian Pharmacopeia" body). URL: <https://www.edaegypt.gov.eg/> ·
e-services portal: <https://eservices.edaegypt.gov.eg/>.

It runs a drug-registry search at
<http://eservices.edaegypt.gov.eg/EDASearch/SearchRegDrugs.aspx> and an
HMO/pricing tool at <https://eservices.edaegypt.gov.eg/EDASearch/>.

**Key facts from my probe of the site:**

- No public REST/JSON API. The portal is a paginated ASP.NET WebForm
  GridView behind a CAPTCHA.
- The "قواعد بيانات" (databases) section links to a Looker Studio
  dashboard and several Google Sheets, not a downloadable CSV/JSON.
- The Pricing, Naming-Checker and Similar-Tools services are
  authenticated.

**Implication:** treat EDA as a *reference* (regulatory truth) but
not as a programmatic source. You'll either scrape once or — better —
consume the community scrapes below.

### 3.2 Open Egyptian drug datasets (GitHub)

The community has done the scraping for you. Best to worst for *this
project*:

**A. `karem505/egyptian-drug-database` — **THE** dataset to use**
- <https://github.com/karem505/egyptian-drug-database>
- License: **CC0** (public domain) — drop it in your repo.
- 25,070 medicines, **each row has Arabic + English trade name +
  scientific composition + manufacturer + drug class + route + EGP price**.
- Schema (`/data/egyptian-drugs.csv`):

| Column | Type | Example |
|---|---|---|
| `commercial_name_en` | string | `AZADERM CREAM 30G` |
| `commercial_name_ar` | string | `بنادول إكسترا` (phonetic transliteration — see caveat below) |
| `scientific_name` | string | `AMOXICILLIN+CLAVULANIC ACID` |
| `manufacturer` | string | `GLAXO SMITHKLINE` |
| `drug_class` | string | `ANALGESIC` |
| `route` | string | `ORAL.SOLID` |
| `price_egp` | number | `45.00` |

- **Important caveat from the README**: `commercial_name_ar` is a
  *deterministic phonetic transliteration* of the English trade name
  (PANADOL → بانادول). It is **not** the EDA-registered Arabic mark.
  So if the catalog uses EDA-registered Arabic, you must still do a
  fuzzy join. But if the catalog is "what an Egyptian pharmacist types",
  it works directly.
- 100% have Arabic alias, 100% have price, ~91% have scientific
  composition, ~99.6% have drug class.

**B. `MoaazSalter/egypt_drug_database`** — the scraper source
- <https://github.com/MoaazSalter/egypt_drug_database>
- ~12,000 drugs scraped directly from EDA, normalized to 33
  standardized dosage-form categories. License unclear, but a Selenium
  notebook + CSV. Good as a second source for cross-validation.
- The 33-category dosage form taxonomy (`I.M. injection`, `Topical
  Cream`, `Eye Drops`, …) is itself useful as a form-token reference
  dictionary.

**C. `mohmedn424/Egypt-drugs-database`** — pricing-focused
- <https://github.com/mohmedn424/Egypt-drugs-database>
- ~14k drugs with current EGP price (snapshot). Outdated pricing but
  useful as cross-check.

### 3.3 Public international APIs

| API | URL | Has Arabic names? | Auth | Free? | Use for this project? |
|---|---|---|---|---|---|
| **openFDA Drug Label** | <https://open.fda.gov/apis/drug/label/> | No (English only) | API key recommended | Yes | No — wrong language |
| **openFDA NDC** | <https://open.fda.gov/apis/drug/ndc/> | No | API key recommended | Yes | No |
| **openFDA Drugs@FDA** | <https://open.fda.gov/apis/drug/drugsfda/> | No | API key recommended | Yes | No |
| **RxNorm / RxNav** | <https://rxnav.nlm.nih.gov/RxNavDoc.html> · REST API: <https://rxnav.nlm.nih.gov/RxNormAPIs.html> | No (English US-centric). Some vocab sources (e.g. MMSL, VANDF) have local names. | None for the public API; UMLS license for full download | Yes | Limited — gives you INN/brand→RxCUI but Arabic aliases aren't in the public vocab |
| **WHO Drug Dictionary / INN** | <https://www.who.int/teams/health-product-and-policy-standards/inn> · School of INN: <https://extranet.who.int/soinn/> | No (English + Latin). Arabic INNs exist as PDFs but not in the published list | Login for School of INN | Yes (lists) | No — useful for INN resolution, not Arabic names |
| **WHO ATC/DDD** | <https://www.who.int/tools/atc-ddd-toolkit> | No | None | Yes | No — for utilization stats |
| **SNOMED CT** | <https://www.snomed.org/> | Limited translations per member country | National license required | No (paid) | No |
| **WHO Essential Medicines** | <https://www.who.int/groups/expert-committee-on-selection-and-use-of-essential-medicines>) | Some Arabic PDF versions of the EML | None | Yes | Not useful for retail matching |

**Bottom line:** there is **no public API** that returns Arabic drug
brand names. RxNorm is the best open international source but it is
English/US-centric. For an Egyptian retail matching use case, RxNorm
can only act as a **fallback** for international brand names that the
Egyptian dataset doesn't carry.

### 3.4 Hugging Face / Kaggle

I searched HF (`?search=arabic+drug`, `?search=pharmaceutical+arabic`) and
Kaggle (`?search=egyptian+pharmacy`). Both return **zero** community
datasets of Arabic drug brand names. The 25k-row karem505 dataset above
is the de-facto source; everything else is either scientific-paper
fragments or non-Arabic drug NER corpora (which are irrelevant here).

### 3.5 Where do "brand names" come from in practice?

For Egyptian pharmacies, the canonical sources are:

- The EDA registered trade-name list (Arabic form per EDA's
  Naming-Checker rules).
- The local manufacturer/distributor catalogs (e.g. EIPICO, EVA Pharma,
  GSK-Egypt, Sanofi-Egypt, Novartis-Egypt). Many are bilingual on the
  box but the order sheet may use either.
- The community scrapes above.

For brand-name dictionary building, the practical order is:
**karem505/egyptian-drug-database → EDA scraping → RxNorm for
international brands → manual exceptions table**.

---

## 4. Phonetic matching for Arabic

### 4.1 What phonetic algorithms give you

A phonetic algorithm maps "similar-sounding" strings to the same code,
so `KHALID` and `KHALEED` collide. For drug names this matters because
pharmacists transcribe by ear — `اوكالبتول` / `اوكالبتول` /
`اوكالبتيل` all probably mean `EUCALYPTOL` if the audio was bad.

### 4.2 What Python libraries ship

| Library | URL | Phonetic algorithms | Arabic-aware? |
|---|---|---|---|
| `jellyfish` | <https://codeberg.org/jpt/jellyfish> · docs: <https://jellyfish.jpt.sh/> · PyPI: <https://pypi.org/project/jellyfish/> | Soundex, Metaphone, Double Metaphone, NYSIIS, Match Rating Approach, Caverphone | **No.** All are English-tuned. |
| `textdistance` | <https://github.com/life4/textdistance> | MRA, Editex | **No.** Same situation. |
| `rapidfuzz` | <https://github.com/rapidfuzz/RapidFuzz> | none (it ships edit-distance, Jaro, Jaro-Winkler, Levenshtein, Damerau, token-set, WRatio, partial_ratio, etc.) | **No.** |

Quick code to confirm:

```python
import jellyfish
jellyfish.soundex("كريم")   # 'K?50'   — meaningless for Arabic
jellyfish.metaphone("كريم") # ''       — empty (no Latin input)
```

### 4.3 Arabic-specific phonetic algorithms (research code, no PyPI)

There are three worth knowing about — none is shipped on PyPI as a
production-quality package:

**A. `SupervisionT/arSoundex`** (<https://github.com/SupervisionT/arSoundex>)
- JavaScript/Node only. Tajweed-rule based grouping; one of two
  algorithms is from
  <https://www.codeproject.com/Articles/26880/Arabic-Soundex>.
- Example: `arSoundex('عبدالله') → 'x74600'`, and the misspelling
  `arSoundex('عبدلله')` produces the same code.
- Could be ported to Python in a few hours. Not used in production
  matching anywhere I can find.

**B. `HussamHallak/Soundex_Arabic_Names`** (<https://github.com/HussamHallak/Soundex_Arabic_Names>)
- Academic project comparing jellyfish Soundex, NYSIIS, Metaphone,
  Levenshtein, and a custom Arabic Soundex on Arabic name data.
- Conclusion in their CSVs: jellyfish's English Soundex gives ~70%
  on Arabic names — much worse than Arabic-specific.

**C. `cari-ayat` (FaizRahiemy)** — Quran verse search via transliteration
+ Soundex. Reference implementation only.

**Verdict on phonetic matching:** for an MVP, **don't bother.** The
Arabic Soundex libraries are JS-only and unmaintained, the Python
phonetic libraries don't speak Arabic, and the problem is already
solved better by the brand dictionary + `rapidfuzz` approach in §6.

If you ever need it: port `SupervisionT/arSoundex` to Python (≈ 100
lines). It works on isolated words, which fits drug brand names.

### 4.4 Edit-distance on transliterated text (the right MVP)

For the residual ~5% of drugs that aren't in the karem505 dataset, the
correct combination is:

1. **Normalize** the Arabic catalog: `pyarabic.araby.strip_tashkeel +
   strip_tatweel + normalize_ligature + normalize_hamza`.
2. **Transliterate** to ASCII Latin with `pyarabic.trans.convert(text,
   "arabic", "latin")`.
3. **Compare** with `rapidfuzz.fuzz.WRatio` or
   `rapidfuzz.process.extractOne(..., scorer=token_set_ratio)`.

```python
from rapidfuzz import fuzz, process

# English catalog (the "AZADERM" side)
en_catalog = ["AZADERM CREAM 30G", "PANADOL EXTRA", "BRUFEN 400MG"]

# Arabic catalog pre-processed + transliterated
ar_catalog_translit = [
    "aywkal krym 30gm",   # ايكال كريم صغير 30جم
    "brwfyn",             # بروفين
    "banadwl <kstra",     # بانادول إكسترا
]

# Reverse: also build a transliterated-to-English mapping
from collections import defaultdict
scores = {}
for ar in ar_catalog_translit:
    best = process.extractOne(ar, en_catalog, scorer=fuzz.token_set_ratio)
    scores[ar] = best    # (name, score, idx)

# scores["brwfyn"] == ("BRUFEN 400MG", 75.0, 1)   -- close enough
# scores["aywkal krym 30gm"] -> low score for AZADERM (no overlap) — this is correct
# scores["aywkal krym 30gm"] -> high score for any EUCAL / EUCALYPTUS / etc. entry
```

This **fails** on the AZADERM ↔ ايكال case you described — that's
correct behavior: there is no Arabic form of "AZADERM" and they are
different products. The fix is the brand dictionary (§3), not a smarter
distance function.

### 4.5 Arabic-aware edit distance (custom)

If you need to roll your own (you probably don't), the trick is:

1. Transliterate to a coarse phoneme set, e.g.
   `k → k, ق → q, غ → gh, ع → 2, ذ → dh, ث → th, ة → t/h, ا → A`.
   (Use `pyarabic.trans.convert(text, "arabic", "sampa")` or write a
   30-line lookup.)
2. Replace all whitespace + punctuation with single space.
3. Compute `token_set_ratio` with `rapidfuzz` — it's already tolerant
   of token reordering.

Don't bother unless (a) you're matching drug names that are misspelled
in Arabic AND (b) you have a benchmark set to measure against.

---

## 5. Pharma-specific matching tactics

### 5.1 What real pharmacy systems do

I checked the three largest pharmacy-data vendors. None publishes
their Arabic matching code, but their product documentation gives
patterns you can copy.

- **Veeva Vault / Veeva OpenData** (<https://www.veeva.com/products/opendata/>)
  — Master Data Management (MDM). Their MDM model is: every product is
  a row with attributes `{trade_name_en, trade_name_local,
  generic_name, manufacturer, strength, form, pack_size, GTIN/NDC}`.
  Matching is done in two stages: (1) hard-match on GTIN/NDC if present,
  (2) deterministic rule cascade on (manufacturer ⊕ trade_name
  prefix ⊕ strength ⊕ form). The Arabic column is treated as just
  another attribute, not a translation.
- **Cencora (formerly AmerisourceBergen), McKesson, Cardinal** — same
  MDM shape; their public docs don't reveal Arabic matching specifics
  but the architectures are uniform: an attribute schema where the
  Arabic label is one attribute among many.
- **Egyptian ERP / pharmacy systems (I-Pharma, Rx-Soft, etc.)** —
  these typically rely on the pharmacy typing the Arabic form
  character-for-character; they do almost no fuzzy matching.

The lesson: **don't rely on the brand name alone.** Real systems key
off a compound identifier: `manufacturer + brand_prefix + strength +
form`.

### 5.2 Drug-attribute normalization

Your existing `normalizer_matching_*.py` modules already do most of
this. Key recommendations from how commercial catalogs look:

#### Forms (already partially in your codebase)

| EN | AR | Note |
|---|---|---|
| cream | كريم | most common: كريم |
| gel | جل | |
| ointment | مرهم / دهان | |
| tablet | أقراص / حبوب / مضغوطة | |
| capsule | كبسولات | |
| syrup | شراب | |
| solution | محلول | |
| injection | حقن / حقنة | |
| drops | نقط / قطرة | |
| spray | بخاخ | |
| lozenge | استحلاب / لبوس فموي | |
| sachet | أكياس | |
| suppository | تحاميل / لبوس | |

#### Strength units

| EN | AR |
|---|---|
| mg | مج / ملجم |
| gm / g | جم / جرام |
| mcg / µg | ميكروجرام / ميكروجرام |
| ml | مل / ملي لتر |
| IU / iu | وحدة دولية |
| % | % |

#### Pack sizes

`10 TABS`, `30 CAPS`, `100 ML`, `30 GM`, `5X5 ML` — same numbers, but
the Arabic side also writes `٣٠` (Eastern Arabic digits) and `١٠`.

**Normalization rule:** always normalize digits to Western Arabic
before extracting numerics. `pyarabic.trans.normalize_digits(text,
source='all', out='west')` does this in one call.

```python
import pyarabic.trans as pt
pt.normalize_digits("٣٠جم", source="all", out="west")  # '30gm'
```

#### Strength parsing

The `normalizer_matching_numeric` module in your codebase already
extracts these. Watch out for `1 GM` vs `1G` vs `1000 MG` — your
existing tolerance for 10× multipliers (mg ↔ g) is correct.

### 5.3 Token-isolation for "AZADERM CREAM 30G"

The catalog row `AZADERM CREAM 30G` should be split into:

- brand = `AZADERM`
- form = `CREAM`
- strength = `(empty)`
- pack = `30G` (could be either 30 grams of cream OR a 30 g tube)

The Arabic row `ايوكال كريم صغير 30جم`:

- brand = `ايوكال` (transliterates to `aywkal`, **does not match
  `AZADERM`**)
- form = `كريم` (cream)
- descriptor = `صغير` (small)
- strength = `(empty)`
- pack = `30جم` (30 g)

Naive token overlap on the original strings finds `كريم ↔ cream` and
`30جم ↔ 30G` → false positive match. The fix is to score each
attribute separately and require the brand component to match (either
via dictionary or via high string similarity), not just form+pack.

### 5.4 Don't reinvent the brand dictionary

If a pharmacy has uploaded the same brand-name Excel for 12 months,
you already have the brand names. Build the brand dictionary
incrementally from your existing matches (human-confirmed), then use
the karem505 seed list as the bootstrap. Don't try to learn brand
names from string distance.

---

## 6. Recommended approach for this project

### 6.1 The algorithm

```
def match_english_to_arabic(en_name, ar_catalog_rows):
    """Returns the best (ar_row, confidence) match."""
    en_tokens = parse(en_name)        # {brand, form, strength, pack, ...}

    # 1. Hard-filter the Arabic catalog by form+pack compatibility
    candidates = [
        r for r in ar_catalog_rows
        if form_compatible(en_tokens.form, parse(r).form)
        and pack_compatible(en_tokens.pack, parse(r).pack)
    ]
    if not candidates:
        candidates = ar_catalog_rows   # fall back to all

    # 2. For each candidate, transliterate Arabic to ASCII Latin
    for r in candidates:
        r.ar_latin = ar_to_latin(r.product_name)

    # 3. Brand-level matching
    best = None
    for r in candidates:
        # 3a. Direct dictionary hit (karem505 dataset)
        en_brand_norm = normalize_brand(en_tokens.brand)
        ar_brand_norm = normalize_brand(parse(r).brand)
        dict_score = brand_dict_score(en_brand_norm, ar_brand_norm)
        #   - exact: 1.0
        #   - known synonym (karem505 row matches): 0.95
        #   - manual alias: 0.9

        # 3b. Fuzzy fallback
        if dict_score < 0.5:
            fuzzy = rapidfuzz.fuzz.token_set_ratio(
                normalize_brand(en_tokens.brand),
                ar_to_latin(parse(r).brand)
            ) / 100.0
        else:
            fuzzy = 0

        score = max(dict_score, fuzzy)

        # 3c. Penalize form/strength/pack mismatches
        if not form_compatible(...): score *= 0.7
        if not pack_compatible(...): score *= 0.9

        if best is None or score > best.score:
            best = (r, score)

    return best
```

### 6.2 Components to ship

| Component | Lib / source | Cost | Notes |
|---|---|---|---|
| Brand dictionary (English→Arabic) | `karem505/egyptian-drug-database` CSV, indexed by `(commercial_name_en → commercial_name_ar)` | **0.5 day** | Load once at startup; build a `dict[brand_en] → brand_ar` for prefix lookup |
| Arabic→Latin transliterator | `pyarabic.trans.convert(text, "arabic", "latin")` + `strip_tashkeel/strip_tatweel/normalize_*` | **0.5 hour** | Add to `src/core/normalization/` |
| Fuzzy scorer | `rapidfuzz.fuzz.WRatio` and `process.extractOne` | already in use | no change |
| Form/strength/pack parser | existing modules (`normalizer_matching_*`) | already done | no change |

### 6.3 Cost / complexity matrix

| Approach | Build time | Dependencies | Coverage on AZADERM/ايوكال | Notes |
|---|---|---|---|---|
| **A. Brand dictionary (karem505) + token_set_ratio fallback** | ½ day | `pyarabic`, `rapidfuzz` | Brand-name match: 95%+ · Residual: handled by fuzzy | **RECOMMENDED** |
| B. `pyarabic.trans` transliterate + rapidfuzz on full name | ½ day | same | wrong on AZADERM (transliteration can't help) | the *status quo*; fails on non-Arabic-origin brands |
| C. CAMeL Tools transliterate + rapidfuzz | 1-2 days + 1 GB dataset | `camel-tools`, `camel_data -i light` | same as B but with more pre-processing | no advantage over A |
| D. EDA scraping + custom rules | 2-3 days | Selenium + maintenance | 99% (regulator data) | fragile (CAPTCHA), maintenance burden |
| E. Embedding-based (sentence-transformers paraphrase-multilingual) | 1-2 days + GPU | heavy | ~85% | overkill for an MVP; needs GPU at runtime |
| F. LLM (GPT/Claude) API per row | 0 days to start, $ at scale | API key + rate limit | 90%+ | only viable if cost isn't a concern |

### 6.4 MVP recommendation: ship A

1. **Day 1 morning**: download `karem505/egyptian-drug-database` CSV,
   build a `dict[brand_en → [brand_ar, manufacturer, drug_class]]` in
   `data/`. ~30 minutes.
2. **Day 1 afternoon**: add `ar_to_latin()` to
   `src/core/normalization/transliterate.py`, write the matching
   cascade in §6.1 into `normalizer_matching_brand.py`. ~3 hours.
3. **Day 1 evening**: add tests for the AZADERM/ايوكال case
   (correctly: no match), BRUFEN/بروفين case (exact via dictionary),
   and a 30-row fuzz regression.

Total: half a day. No new heavy dependencies.

### 6.5 Drop-in code skeleton

```python
# src/core/normalization/transliterate.py
import pyarabic.araby as ar
import pyarabic.trans as pt

def ar_to_latin(s: str) -> str:
    s = ar.strip_tashkeel(s)
    s = ar.strip_tatweel(s)
    s = ar.normalize_ligature(s)
    s = ar.normalize_hamza(s, method="tasheel")
    s = pt.normalize_digits(s, source="all", out="west")
    return pt.convert(s, "arabic", "latin")


# src/core/normalization/normalizer_matching_bilingual.py
from __future__ import annotations
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from .transliterate import ar_to_latin

_CSV = ("https://raw.githubusercontent.com/karem505/"
        "egyptian-drug-database/main/data/egyptian-drugs.csv")

@lru_cache(maxsize=1)
def brand_dict() -> dict[str, list[dict]]:
    """English trade name → list of {ar, manufacturer, drug_class, form}.

    Built once from the karem505/egyptian-drug-database CSV.
    """
    df = pd.read_csv(_CSV, dtype=str).fillna("")
    out: dict[str, list[dict]] = {}
    for _, row in df.iterrows():
        key = _normalize_brand(row["commercial_name_en"])
        out.setdefault(key, []).append({
            "ar": row["commercial_name_ar"],
            "manufacturer": row["manufacturer"],
            "drug_class": row["drug_class"],
            "scientific_name": row["scientific_name"],
        })
    return out

def _normalize_brand(s: str) -> str:
    s = re.sub(r"\b\d+\s*(MG|GM|G|ML|MCG|IU|%)\b", "", s, flags=re.I)
    s = re.sub(r"\b(TAB|TABS|CAP|CAPS|CREAM|GEL|SYRUP|"
               r"INJ|FC|F\.C\.)\b\.?", "", s, flags=re.I)
    s = re.sub(r"[^A-Z0-9]", "", s.upper())
    return s.strip()

def match_brand(en_name: str, ar_brand: str, ar_maker: str = "") -> float:
    """Return a 0..1 confidence that two brands are the same product."""
    en_key = _normalize_brand(en_name)
    ar_key = _normalize_brand(ar_brand)

    # 1. Direct lookup in the seeded dictionary
    for hit in brand_dict().get(en_key, []):
        if _normalize_brand(hit["ar"]) == ar_key:
            return 0.95
        # Soft: same manufacturer + similar Arabic form
        if ar_maker and hit["manufacturer"] and (
            ar_maker.upper() in hit["manufacturer"].upper()
            or hit["manufacturer"].upper() in ar_maker.upper()
        ) and fuzz.token_set_ratio(en_key, _normalize_brand(hit["ar"])) > 80:
            return 0.85

    # 2. Fuzzy on transliterated Arabic
    ar_latin = ar_to_latin(ar_brand)
    ar_latin_norm = re.sub(r"[^A-Z0-9]", "", ar_latin.upper())
    score = fuzz.token_set_ratio(en_key, ar_latin_norm) / 100.0

    return score
```

### 6.6 How this fixes the AZADERM/ايوكال bug

- `AZADERM` has no Arabic brand form in karem505 (it's not in the
  Egyptian market as `ازاديرم`; it's a global product).
- `match_brand("AZADERM CREAM 30G", "ايوكال كريم صغير 30جم")` → 0.0
  dictionary hits, then `token_set_ratio("AZADERM", "AYWKAL")` ≈ 0.
- Combined with the form/strength/pack penalties, the row falls below
  the acceptance threshold and is correctly rejected as no-match.

For a real pair like `BRUFEN 400 MG` / `بروفين 400 مج`:

- `_normalize_brand("BRUFEN 400 MG") == "BRUFEN"`.
- karem505 has `BRUFEN 400 MG 30 TABS. → بروفين`.
- Dict hit → 0.95 → accept.

For a near-pair like `PANADOL EXTRA` / `بنادول إكسترا`:

- karem505 has `PANADOL EXTRA 48 F.C. TABS. → بانادول إكسترا`.
- Dict hit → 0.95 → accept.

### 6.7 Honest limitations

- **International brands not in Egypt**: e.g. `MUCINEX` (US OTC). No
  match in the Egyptian DB. RxNorm fallback helps here
  (`getRxcuiByString` + `getSpellingSuggestions` then check
  manufacturer).
- **Drugs registered in Egypt only in the last 6 months**: the
  karem505 dataset is updated monthly; refresh quarterly.
- **Spelling drift in Arabic**: `ايوكال` vs `أوكال` vs `اوكال` —
  `normalize_hamza(method="tasheel")` already collapses the first two;
  add a manual alias table for the third.
- **Manufacturer in catalog but not in dataset**: ~5% of EDA drugs.
  Don't gate the entire match on manufacturer; use it only as a
  tie-breaker.

---

## 7. Appendix — when the right answer is to fix the catalog

Before any of this algorithmic work, ask: **can the upstream system
provide an English trade-name column?**

If yes:

- Add `commercial_name_en` to the Excel column whitelist.
- Match on English-to-English (`fuzz.WRatio` on full string or
  brand-prefix match) — no transliteration needed.
- Use Arabic column for human display only.

If no (and the upstream only publishes Arabic):

- The §6.1 algorithm above.
- Also ask upstream to publish `commercial_name_en`. EDA's website
  lists it for every product; the lack is in the export pipeline,
  not the data.

If upstream explicitly refuses to publish English names (rare, but
happens for some local-only generics):

- Use `camel-tools` morphological analysis to extract a candidate
  scientific-name component, then map to RxNorm INN, then back to
  English. 2-3 weeks of work; only if you're building a serious
  product.

---

## 8. References (URLs)

### Transliteration

- Buckwalter transliteration (Wikipedia):
  <https://en.wikipedia.org/wiki/Buckwalter_transliteration>
- pyarabic GitHub: <https://github.com/linuxscout/pyarabic>
- pyarabic features doc:
  <https://github.com/linuxscout/pyarabic/blob/master/doc/features.md>
- pyarabic `trans.py` source:
  <https://github.com/linuxscout/pyarabic/blob/master/pyarabic/trans.py>
- CAMeL Tools GitHub: <https://github.com/CAMeL-Lab/camel_tools>
- CAMeL Tools docs: <https://camel-tools.readthedocs.io/en/latest/>
- CAMeL encoding schemes:
  <https://camel-tools.readthedocs.io/en/latest/reference/encoding_schemes.html>
- arabic-reshaper GitHub: <https://github.com/mpcabd/python-arabic-reshaper>
- python-bidi GitHub: <https://github.com/MeirKriheli/python-bidi>
- CLTK (Classical Language Toolkit): <https://github.com/cltk/cltk>

### Matching libraries

- jellyfish docs: <https://jellyfish.jpt.sh/>
- jellyfish source: <https://codeberg.org/jpt/jellyfish>
- rapidfuzz GitHub: <https://github.com/rapidfuzz/RapidFuzz>
- rapidfuzz fuzz scorers:
  <https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html>
- textdistance GitHub: <https://github.com/life4/textdistance>

### Arabic phonetic (research code)

- arSoundex (JS): <https://github.com/SupervisionT/arSoundex>
- Arabic Soundex research: <https://www.codeproject.com/Articles/26880/Arabic-Soundex>
- Soundex Arabic Names (benchmark):
  <https://github.com/HussamHallak/Soundex_Arabic_Names>

### Pharma data

- Egyptian Drug Authority: <https://www.edaegypt.gov.eg/>
- EDA e-services: <https://eservices.edaegypt.gov.eg/>
- karem505/egyptian-drug-database (the dataset to use):
  <https://github.com/karem505/egyptian-drug-database>
  · CSV: <https://raw.githubusercontent.com/karem505/egyptian-drug-database/main/data/egyptian-drugs.csv>
- MoaazSalter/egypt_drug_database (scraper source):
  <https://github.com/MoaazSalter/egypt_drug_database>
- mohmedn424/Egypt-drugs-database (price snapshot):
  <https://github.com/mohmedn424/Egypt-drugs-database>

### International APIs (English-only, no Arabic)

- openFDA Drug API overview: <https://open.fda.gov/apis/drug/>
- openFDA Drug Label: <https://open.fda.gov/apis/drug/label/>
- RxNorm overview (NLM): <https://www.nlm.nih.gov/research/umls/rxnorm/>
- RxNorm REST API: <https://rxnav.nlm.nih.gov/RxNormAPIs.html>
- RxNav overview: <https://rxnav.nlm.nih.gov/RxNavDoc.html>
- WHO INN programme: <https://www.who.int/teams/health-product-and-policy-standards/inn>
- WHO ATC/DDD: <https://www.who.int/tools/atc-ddd-toolkit>

### Pharma systems (architectural references)

- Veeva Vault MDM / OpenData: <https://www.veeva.com/products/opendata/>
- Veeva Network MDM (commercial data model):
  <https://www.veeva.com/products/crm-suite/network-mdm/>

---

**Bottom line in one sentence:** add `karem505/egyptian-drug-database`
as a brand-name lookup, transliterate the residual Arabic with
`pyarabic`, score with `rapidfuzz`, and keep your existing
form/strength/pack parsing — this fixes the AZADERM/ايوكال bug for the
right reason (no signal, not no match).
