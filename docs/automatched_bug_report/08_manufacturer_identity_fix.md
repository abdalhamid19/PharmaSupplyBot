# 08 — الإصلاح البنيوي لهوية الشركة المصنّعة (Manufacturer Identity: Recognise, Never Guess)

> تنفيذ التوصية 3.1 من التقرير 06 — الخيار 2: الاعتماد على `companyName` الصريح فقط، وعدم تخمين شركة من اسم الصنف.

---

## 1. المشكلة البنيوية

`extract_manufacturer_from_name()` القديمة كانت تعتبر **آخر token غير رقمي وغير موجود في قائمة الكلمات العامة** هو الشركة المصنّعة:

```python
def extract_manufacturer_from_name(name: str) -> str | None:
    tokens = normalize_text(name).split()
    for token in reversed(tokens):
        if token.isdigit():
            continue
        if token in _GENERIC_IDENTITY_TOKENS:   # 27 كلمة فقط: TAB, GEL, CREAM...
            continue
        return token                            # ← أي كلمة أخرى = "شركة"!
    return None
```

والـ candidate كان يرتد لنفس التخمين عند غياب الحقل الصريح:

```python
def extract_manufacturer_from_candidate(candidate_name, company_name=None, supplier_name=None):
    if company_name:  ...
    if supplier_name: ...
    return extract_manufacturer_from_name(candidate_name)   # ← تخمين مرة أخرى
```

## 2. القياس الكمي على البيانات الحقيقية

قِيست الخوارزمية على **كل** أسماء الأصناف المميزة في `state/manual_review_decisions.db`:

```
distinct item names inspected:                    1232
heuristic claims a manufacturer:                  1230  (99.8%)
whitelist (KNOWN_MANUFACTURERS) claims one:          10  (0.8%)
heuristic invents one where whitelist finds none:  1220  (99.0%)
```

### عينة من "الشركات" المُختلَقة

| اسم الصنف | "الشركة" المُختلَقة | ما هي فعلاً |
|---|---|---|
| `ABIMOL EXTRA 20 TAB.` | `EXTRA` | واصف جرعة/تركيبة |
| `ACTI-COLLA C 30SACHETS` | `SACHETS` | وحدة تغليف |
| `ACTI-COLLA ADVANCE 10 SACHET` | `SACHET` | وحدة تغليف |
| `ACYCLOVIR 400 MG 35 TAB` | `ACYCLOVIR` | المادة الفعالة |
| `ADAPALENE GEL 30 GM` | `ADAPALENE` | المادة الفعالة |
| `ACTIVE HAIR OIL 120 ML` | `OIL` | شكل دوائي |
| `ACTRAPID HM 100 I.U./ML 10 ML VIAL` | `U` | حرف من وحدة القياس! |
| `ALBUNORM 20% I.V.INFUSION` | `INFUSION` | شكل دوائي |
| `ACHTENON 30 TABS` | `ACHTENON` | اسم تجاري |
| `AGGREX 75 MG 60 TAB` | `AGGREX` | اسم تجاري |
| `ULTRA PANADOL 10 TAB` | `PANADOL` | اسم تجاري |
| `CO AVAZIR 5GM EYE OINTMENT` | `AVAZIR` | جزء من اسم المنتج |

**الخلاصة:** 99% من "الشركات" المستخرجة كانت وهمية. هذه الشركات الوهمية تتصادم مع `companyName` الحقيقي فتنتج "تضارباً" يمنع حفظ تطابقات سليمة.

## 3. سبب فشل النهج القديم بنيوياً

قائمة `_GENERIC_IDENTITY_TOKENS` تحتوي 27 كلمة (TAB, GEL, CREAM, ML...). لكن فضاء الكلمات التي **ليست** شركات مصنّعة يشمل:
- كل الأسماء التجارية للأدوية (آلاف)
- كل المواد الفعالة (آلاف)
- كل واصفات الجرعة (EXTRA, ULTRA, ADVANCE, FORTE, PLUS...)
- كل وحدات التغليف والقياس

**توسيع القائمة عاجز رياضياً** — القائمة يجب أن تحتوي كل كلمة في عالم الأدوية ما عدا أسماء الشركات. النهج معكوس: يجب أن نتعرّف على الشركات، لا أن نستثني كل ما ليس شركة.

## 4. الإصلاح المُطبَّق

### 4.1 جانب الصنف (query): تعرُّف لا تخمين

```python
def extract_manufacturer_from_name(name: str) -> str | None:
    """Return a curated manufacturer named inside the text, else None."""
    if not name:
        return None

    parenthesised = _parenthesised_manufacturer(name)   # "(ORCHIDIA)" أولوية
    if parenthesised:
        return parenthesised

    recognised = [
        token for token in normalize_text(name).split()
        if token in KNOWN_MANUFACTURERS                 # ← قائمة مُنسَّقة فقط
    ]
    return recognised[-1] if recognised else None
```

- المصدر: `KNOWN_MANUFACTURERS` الموجودة أصلاً في `normalizer_manufacturer_extraction.py` (31 شركة مصرية/عالمية: ORCHIDIA, ORA, EVA, PHARCO, AMOUN, EIPICO, GSK, SANOFI...).
- الأقواس لها أولوية لأنها أكثر صيغة صريحة: `METHYL FOLATE (ORCHIDIA) 30 CAPS`.
- آخر token مُتعرَّف عليه يفوز (الشركات تُكتب عادة في نهاية أسماء الأصناف المصرية).
- **أي كلمة غير موجودة في القائمة → `None`** (لا تخمين).

### 4.2 جانب المرشح (candidate): حقول صريحة فقط

```python
def extract_manufacturer_from_candidate(
    candidate_name: str,
    company_name: str | None = None,
    supplier_name: str | None = None,
) -> str | None:
    """Return the candidate's manufacturer from explicit API fields only.

    `candidate_name` is accepted for call-site compatibility but deliberately
    unused: guessing a company from a product name is what produced phantom
    conflicts. When Tawreed sends no company or supplier, the answer is None.
    """
    del candidate_name  # explicit fields only; never guess from the name
    return _first_token(company_name) or _first_token(supplier_name)
```

**الفرق الجوهري:** لا ارتداد للتخمين من الاسم. إذا لم يرسل Tawreed شركة أو مورّداً، الإجابة `None` — و`None` تعني "لا تضارب".

### 4.3 `manufacturer_conflict` بلا تغيير

`None` على أي جانب = لا تضارب (كان كذلك من قبل، والآن `None` أصبحت الحالة الشائعة والصحيحة بدل شركة وهمية).

## 5. الأثر على المستخدمين الثلاثة للدالة

| الموضع | الأثر |
|---|---|
| `manual_review_helpers.should_skip_auto_save` (الحفظ التلقائي) | لا رفض وهمي عند تفعيل `enable_manufacturer_check` — التضاربات الحقيقية فقط تُمنع |
| `product_matching_acceptance._manufacturer_rejection` (قبول المطابقة) | الفحص (المعطّل افتراضياً) أصبح ذا معنى: يرفض ORCHIDIA-vs-ORA ولا يرفض EXTRA-vs-GSK |
| `matching_confidence.match_confidence` (عامل f6 بوزن 0.13) | كان يخصم 0.13 من ثقة معظم التطابقات بسبب تضارب وهمي؛ الآن يخصم فقط عند تضارب حقيقي |

**النقطة الأخيرة مهمة:** الخلل كان يخفض درجة الثقة لـ ~99% من التطابقات بشكل غير مبرَّر — أثر واسع يتجاوز مسألة الحفظ.

## 6. الاختبارات

`tests/core/identity/test_manufacturer_identity_explicit_only.py` — **17 اختباراً في 4 مجموعات:**

### مجموعة 1: لا تخمين من اسم الصنف (6 اختبارات)
| الاختبار | المُدخَل | المتوقع |
|---|---|---|
| `test_dosage_descriptor_is_not_a_manufacturer` | `PANADOL EXTRA 24 TAB` | `None` |
| `test_packaging_unit_is_not_a_manufacturer` | `ACTI-COLLA C 30SACHETS` | `None` |
| `test_active_ingredient_is_not_a_manufacturer` | `ACYCLOVIR 400 MG 35 TAB` | `None` |
| `test_brand_name_is_not_a_manufacturer` | `ULTRA PANADOL 10 TAB` | `None` |
| `test_product_word_is_not_a_manufacturer` | `CO AVAZIR 5GM EYE OINTMENT` | `None` |
| `test_empty_name_returns_none` | `""` | `None` |

### مجموعة 2: التعرُّف على الشركات المُنسَّقة (4 اختبارات)
| المُدخَل | المتوقع |
|---|---|
| `METHYL FOLATE 30 CAP ORCHIDIA` | `ORCHIDIA` |
| `METHYL FOLATE ORA 30 CAPS` | `ORA` |
| `METHYL FOLATE (ORCHIDIA) 30 CAPS` | `ORCHIDIA` (أولوية الأقواس) |
| `EVA SOMETHING 10 TAB ORCHIDIA` | `ORCHIDIA` (الأخير يفوز) |

### مجموعة 3: المرشح بحقول صريحة فقط (4 اختبارات)
| الحالة | المتوقع |
|---|---|
| `companyName="GSK"` | `GSK` |
| `supplierName="HIKMA PHARMA"` فقط | `HIKMA` |
| لا حقول صريحة | `None` (كان يخمّن من الاسم) |
| حقول فارغة/مسافات | `None` |

### مجموعة 4: سلوك التضارب النهائي (3 اختبارات)
| السيناريو | المتوقع |
|---|---|
| `EXTRA` (وهمي) vs `GSK` | **لا تضارب** — هذا كان يمنع الحفظ |
| `ORCHIDIA` vs `ORA` (كلاهما مُنسَّق) | **تضارب** — الحماية الحقيقية باقية |
| `GSK` vs `GSK` | لا تضارب |

### تحديث اختبار سابق

`tests/reproduction/test_postfix_auto_matched_saving.py`:
- `test_3_manufacturer_flag_opt_in_blocks_save` → `test_3_manufacturer_flag_opt_in_blocks_real_conflict`: الآن يستخدم تضارباً حقيقياً (ORCHIDIA vs companyName `ORA`) بدل الوهمي.
- **اختبار جديد** `test_3b_manufacturer_flag_on_does_not_block_phantom_conflict`: يثبت أن `PANADOL EXTRA` + `GSK` يُحفَظ حتى مع `enable_manufacturer_check=True`.

## 7. النتائج

```
tests/core/identity/                                   17 passed
tests/reproduction/                                    15 passed
tests/test_manufacturer_mismatch.py + matching + ...    98 passed
الحزمة الكاملة:  802 passed, 8 failed
```

مقارنة الإخفاقات قبل/بعد (بـ `git stash` للتغيير فقط ثم `Compare-Object`): **الإخفاقات الثمانية متطابقة تماماً** — لا انحدار. الوحيد الذي تغيّر هو نجاح الاختبارات السبعة الجديدة التي كانت تفشل قبل الإصلاح (وهو المطلوب).

## 8. ما لم يتغيّر (مقصود)

- `manufacturer_conflict()` — منطق المقارنة والعتبة كما هو.
- `enable_manufacturer_check` — يبقى معطّلاً افتراضياً. الفحص أصبح دقيقاً، لكن تفعيله قرار المستخدم.
- `KNOWN_MANUFACTURERS` — لم أوسّعها؛ توسيعها بشركات إضافية من بيانات Tawreed تحسين مستقبلي مستقل (وأي شركة غير مُدرَجة تعني ببساطة "لا معلومة" لا "خطأ").
- `normalizer_manufacturer_extraction.extract_manufacturer_from_name` (دالة مختلفة تُرجع tuple، تُستخدم في مسار `parse_drug`) — كانت تعتمد على القائمة المُنسَّقة أصلاً وهي سليمة.
