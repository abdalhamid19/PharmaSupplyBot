# التحليل التفصيلي الشامل لأخطاء المطابقة (Matching Errors Deep Analysis)

> **التاريخ:** 2026-07-01 · **الفرع:** `main`
> **نطاق التحليل:** خمس حالات مبلَّغ عنها + إعادة فحص خطة `MANUFACTURER_MISMATCH_FIX_PLAN.md` التي *لم تُحلّ المشكلة فعلياً*.
> **قواعد الالتزام:** `docs/project_guidelines.md` (فصل الطبقات، Config مركزي، عدم التفتيت) + `docs/starting_prompt.md` (Surgical / Think Before Coding / No Regression).
> **الحالة:** تحليل + خطة. **لم يُعدَّل أي كود إنتاجي في هذا المستند** — فقط تشخيص بالأدلة وخطة مرتبة.
> **بوابة إلزامية:** تشغيل كل الاختبارات بعد كل تغيير.

---

## 0. الملخص التنفيذي (Bottom Line)

كل الحالات المبلَّغ عنها ترجع إلى **سبب جذري معماري واحد مع ثلاثة أعراض مركّبة**:

> **محرّك المطابقة يقبل مرشحاً «كأنه صحيح» عندما تكون كل tokens الاستعلام
> موجودة داخل المرشح، حتى لو أضاف المرشح token مميِّز يغيّر هوية المنتج
> (JOINT, MAN, ORA...)، لأن درجة التداخل (overlap) تقيس اتجاهاً واحداً فقط
> (query → candidate) ولا يوجد أي فحص «للشركة المُصنّعة» فعّال في الإنتاج.**

الأدلة المباشرة (من تشغيل `explain_best_product_match` فعلياً على الحالات):

| الاستعلام | المرشح | الدرجة | القرار الفعلي (الإنتاج) | صحيح؟ |
|---|---|---|---|---|
| `METHYL FOLATE 30 CAP ORCHIDIA` | `METHYL FOLATE ORA 30 CAPS` | 19.10 | **مقبول** (added-to-cart) | ❌ خطأ |
| `CAL MAG 30TAB` | `CAL MAG JOINT 30 TAB` | 22.12 | **مقبول** | ❌ خطأ |
| `LIMITLESS MILGA MAX 30 TABS` | `LIMITLESS MAN MAX 30 TABS` | 20.62 | **مقبول** | ❌ خطأ |
| `CO_AVAZIR 5GM EYE OINTMENT` | `AVAZIR 0.3 % EYE OINT. 5 GM` | 15.36 | **مقبول** (safe omission) | ⚠️ حدّي |
| `LILI FEMININE WASH 250ML` | `LILIOX 10 SACHETS` | 4.07 | **مرفوض** (not-orderable) | ✅ الرفض صحيح، السبب المُبلَّغ مضلِّل |

> **السبب الجذري المرجّح (الأول):** درجة التداخل غير متماثلة + مفردات
> `DISTINGUISHING_TOKENS` صغيرة جداً وثابتة، فلا تلتقط `JOINT`/`MAN`/`ORA`
> كفروق مميِّزة ⟸ **هذا يفسّر CAL MAG و LIMITLESS و METHYL FOLATE مباشرة**.
>
> **السبب الجذري الثاني:** فحص المُصنّع الذي أُضيف سابقاً **معطّل افتراضياً في
> الإنتاج** (`enable_manufacturer_check = False`) — ولذلك خطة METHYL FOLATE لم
> تُنتج أي تغيير في التشغيل الحقيقي.
>
> **السبب الجذري الثالث (خطير):** حتى عند تفعيل فحص المُصنّع، **الدالة معيبة**:
> تعتبر «آخر كلمة في الاسم» اسمَ شركة، فتُنتج مقارنات هراء مثل `MAG vs JOINT`،
> `AVAZIR vs OINT`، `WASH vs SACHETS` ⟸ رفض عشوائي واسع لو فُعّل.

---

## 1. كيف يعمل خط المطابقة (خلفية ضرورية لفهم كل خطأ)

### 1.1 نقطة الدخول والتدفق

`explain_best_product_match` (`src/core/matching/product_matching.py:42-56`):
1. تُبنى تشخيصات لكل مرشح عبر `_build_candidate_diagnostics`
   (`product_matching_decisions.py`).
2. لكل مرشح: تُحسب درجة (`_match_score_breakdown_for_config`) ثم يُقرَّر القبول
   (`_diagnostic_acceptance` في `product_matching_acceptance.py:388-404`).
3. يُختار الفائز في `_decision_from_diagnostics`.

الإعداد في الإنتاج يُحمَّل مرة واحدة من `config.yaml` عبر
`build_matching_config` (`src/core/config/config_factory.py:60-78`) ويُمرَّر
كـ `bot.config.matching` إلى المطابقة في ثلاث نقاط:
- `src/tawreed/api/tawreed_api_matching.py:80`
- `src/tawreed/api/tawreed_api_flow_matching.py:104`
- `src/tawreed/matching/tawreed_search_logic.py:102`

### 1.2 منطق القبول (Acceptance Tiers)

`acceptance_details → _acceptance_checks` (`matching_rules.py:71-82`) — أربع بوابات
قبول مرتبة، **يكفي نجاح واحدة منها**:

| البوابة | الشرط | الرمز |
|---|---|---|
| اسم مطابق تماماً | `normalized_query == normalized_english_name` | `matching_rules.py:85-97` |
| تداخل عالٍ | `best_overlap ≥ 0.85` | `matching_rules.py:100-106` |
| **درجة متوسطة** | `score ≥ 12.0` **و** `overlap ≥ 0.60` | `matching_rules.py:109-120` |
| درجة رقمية | `score ≥ 20.0` **و** numeric_match **و** `overlap ≥ 0.45` | `matching_rules.py:123-136` |

### 1.3 بوابات الرفض الصلبة (Hard Rejections)

`_check_rejections` (`product_matching_acceptance.py:354-385`) تُرجع رفضاً قبل
حساب أي درجة عند:
- `_candidate_variant_rejection` (نقص token هوية إنجليزي/عربي).
- `compatibility_rejection_reason` (`matching_penalties.py:36-44`) — تعارض
  CONFLICT_GROUP أو وجود DISTINGUISHING_TOKEN إضافي في المرشح.
- `_candidate_component_rejection` (تحليل درجة الدواء).
- **فحص المُصنّع** — فقط لو `enable_manufacturer_check == True`.

### 1.4 درجة التداخل (المفتاح لكل الأخطاء)

`_best_candidate_overlap` (`product_matching_scoring.py:83-88`) = **أقصى** تداخل
بين الاستعلام والاسم الإنجليزي، والاستعلام والاسم العربي. و`_token_overlap_score`
يحسب: *لكل token في الاستعلام، أفضل درجة له في المرشح* (1.0 تطابق، 0.7 احتواء،
0.0 لا شيء)، ثم المتوسط.

> ⚠️ **العيب الجوهري:** القياس **اتجاه واحد** (query → candidate). إذا كان
> الاستعلام مجموعة جزئية من المرشح، يحصل على تداخل 1.0 بغضّ النظر عن الكلمات
> الإضافية في المرشح. أي token إضافي في المرشح **غير مرئي** لدرجة التداخل، ولا
> يُعاقَب إلا إذا كان مُدرَجاً يدوياً في `DISTINGUISHING_TOKENS` أو
> `CONFLICT_GROUPS`.

### 1.5 الدرجة المركّبة والعقوبات

`_score_components` (`product_matching_scoring.py:223-237`):
```
total = max(0,
    sequence*5 + overlap*10 + numeric*5 + exact_bonus + avail_bonus
    - 2.0 * |missing_critical_tokens|
    - 3.0 * |extra_distinguishing_tokens|
    - 10.0 * |conflict_group_pairs|)
```
- `exact_bonus = 2.0` لو احتوى أحد الاسمين الآخر.
- `avail_bonus = +1.0` لو `availableQuantity > 0`، وإلا `-1.5`.

المفردات الثابتة (`src/core/matching_types.py`):
- `DISTINGUISHING_TOKENS` (سطر 122-124): `{ADVANCED, EXTRA, FORTE, MAX, PLUS,
  PRO, SUPER, ULTRA, 2%}` — **9 كلمات فقط**.
- `CRITICAL_TOKENS` (79-121): قائمة أشكال/نكهات.
- `CONFLICT_GROUPS` (125-130): 4 مجموعات (نكهات، فواكه، أشكال موضعية، أشكال حقن).

---

## 2. تشخيص كل حالة بالأدلة (Evidence-Based Case Diagnosis)

> **منهجية الأدلة:** شُغِّلت `explain_best_product_match` فعلياً على الحالات
> الخمس بإعدادين (افتراضي الإنتاج، وفحص المُصنّع مفعّلاً). الأرقام أدناه
> مأخوذة من التشغيل الفعلي وليست تقديراً.

---

### 🔴 الحالة 1 — `CAL MAG 30TAB` ⟵ `CAL MAG JOINT 30 TAB` (مطابقة خاطئة)

**المُدخل:** `CAL MAG 30 TAB` (بعد فصل `30TAB`) → tokens: `{CAL, MAG, 30, TAB}`.
**المرشح:** `CAL MAG JOINT 30 TAB` → tokens: `{CAL, MAG, JOINT, 30, TAB}`.

**خطوة بخطوة:**
1. `_token_overlap_score`: كل tokens الاستعلام الأربعة موجودة حرفياً في المرشح
   ⟹ **overlap = 4/4 = 1.0**.
2. بوابة `_high_overlap_check`: `1.0 ≥ 0.85` ⟹ **تُقبل فوراً**.
3. `compatibility_rejection_reason`: `JOINT` **ليس** في `DISTINGUISHING_TOKENS`
   ولا في أي `CONFLICT_GROUP` ⟹ لا رفض صلب.
4. `_missing_english_identity_reasons`: tokens الهوية للاستعلام `{CAL, MAG}`
   موجودة في المرشح ⟹ لا رفض.
5. لا tokens رقمية إضافية.

**الدرجة الفعلية المقاسة: 22.12 ⟹ مقبول (added-to-cart).**

> **السبب الجذري:** `JOINT` كلمة تغيّر هوية المنتج (كال-ماج عادي ≠ كال-ماج
> للمفاصل) لكنها **خارج كل قوائم العقوبة الثابتة**، ودرجة التداخل الأحادية تمنح
> 1.0 لأن الاستعلام مجموعة جزئية من المرشح.

---

### 🔴 الحالة 2 — `LIMITLESS MILGA MAX 30 TABS` ⟵ `LIMITLESS MAN MAX 30 TABS` (مطابقة خاطئة)

**الاستعلام:** `{LIMITLESS, MILGA, MAX, 30, TABS}`.
**المرشح:** `{LIMITLESS, MAN, MAX, 30, TABS}`.

**خطوة بخطوة:**
1. `_token_overlap_score`: `LIMITLESS=1.0`, `MILGA=0.0` (لا تطابق `MAN` ولا
   احتواء)، `MAX=1.0`, `30=1.0`, `TABS=1.0` ⟹ **overlap = 4/5 = 0.80**.
2. `_high_overlap_check`: `0.80 < 0.85` ⟹ تفشل.
3. `_medium_score_check`: يحتاج `score ≥ 12` **و** `overlap ≥ 0.60`. الدرجة
   المقاسة الفعلية **20.62**، والتداخل 0.80 ⟹ **تُقبل**.
4. `MAN` ليس في `DISTINGUISHING_TOKENS`/`CONFLICT_GROUPS` ⟹ لا رفض صلب.
5. tokens الهوية المشتركة `{LIMITLESS, MAX}` تكفي لتجاوز فحص الهوية.

**الدرجة الفعلية: 20.62 ⟹ مقبول.**

> **السبب الجذري:** `MILGA` و `MAN` علامتان مميّزتان متعارضتان، لكن كلاهما يسجّل
> 0.0 (لا يعاقَب على «عدم التطابق»، فقط لا يُكافَأ)، وبقية الـ4 tokens تكفي
> لتجاوز عتبة الدرجة المتوسطة (12). العتبة **متساهلة** أمام أسماء متشابهة
> شكلياً ومختلفة الهوية.

---

### 🔴 الحالة 3 — `METHYL FOLATE 30 CAP ORCHIDIA` ⟵ `METHYL FOLATE ORA 30 CAPS` (مطابقة خاطئة — خطة سابقة فشلت)

**الاستعلام:** `{METHYL, FOLATE, 30, CAP, ORCHIDIA}`.
**المرشح:** `{METHYL, FOLATE, ORA, 30, CAPS}`.

**خطوة بخطوة (الإنتاج، فحص المُصنّع مُعطّل):**
1. `ORCHIDIA` لا يطابق `ORA` (0.0)، لكن بقية tokens تسجّل عالياً (`CAP`⊂`CAPS`=0.7).
2. الدرجة المقاسة الفعلية **19.10** والتداخل ≈ 0.74 ⟹ تتجاوز الدرجة المتوسطة.
3. `ORCHIDIA` خارج كل قوائم العقوبة ⟹ لا رفض.
4. `enable_manufacturer_check = False` ⟹ **فحص المُصنّع لا يُستدعى إطلاقاً**.

**النتيجة الفعلية: مقبول (19.10). ورغم خطة `MANUFACTURER_MISMATCH_FIX_PLAN.md`
لم يتغيّر شيء في الإنتاج.**

> **لماذا فشلت الخطة السابقة؟** أُضيف الكود والاختبارات فعلاً
> (`src/core/identity/manufacturer_identity.py`،
> `product_matching_acceptance.py:318-385`، `tests/test_manufacturer_mismatch.py`)
> **لكن العتبة الافتراضية `enable_manufacturer_check = False`
> (`src/core/config/config_models.py:62`)** ولا يوجد أي مفتاح في `config.yaml`
> يفعّلها. أي أن الإصلاح موجود **معطّلاً**.
>
> **الأخطر:** عند تفعيله يدوياً، أثبت التشغيل الفعلي أن الدالة
> `extract_manufacturer_from_name` (`manufacturer_identity.py:21-32`) تأخذ
> «آخر token غير عام» كشركة، فتنتج مقارنات خاطئة:
> - `METHYL FOLATE ... ORCHIDIA` ⟹ شركة الاستعلام = `ORCHIDIA` ✅ (صحيح صدفة).
> - `CAL MAG JOINT 30 TAB` ⟹ شركة المرشح = `JOINT` ❌ (JOINT ليست شركة).
> - `AVAZIR ... EYE OINT` ⟹ شركة المرشح = `OINT` ❌.
> - `LILIOX 10 SACHETS` ⟹ شركة المرشح = `SACHETS` ❌.
>
> فالتفعيل الحالي «يصلح» METHYL FOLATE بالصدفة لكنه يكسر مطابقات صحيحة كثيرة
> عبر رفض عشوائي. **لذلك التفعيل المباشر غير آمن — يحتاج إعادة تصميم للدالة.**

---

### ⚠️ الحالة 4 — `CO_AVAZIR 5GM EYE OINTMENT` ⟵ `AVAZIR 0.3 % EYE OINT. 5 GM` (حدّية)

**الاستعلام:** `_` يُحذف ⟹ `{CO, AVAZIR, 5, GM, EYE, OINTMENT}`.
**المرشح:** `%` و`.` تُحذف ⟹ `{AVAZIR, 0, 3, EYE, OINT, 5, GM}`.

**خطوة بخطوة:**
1. `_token_overlap_score`: `CO=0.0`, `AVAZIR=1.0`, `5=1.0`, `GM=1.0`, `EYE=1.0`,
   `OINTMENT`⊃`OINT`=0.7 ⟹ overlap ≈ 0.78.
2. `_numeric_acceptance`: tokens رقمية إضافية `{0, 3}` (من `0.3%`) ⟹
   `_safe_omitted_percentage_concentration` (`product_matching_acceptance.py:303-312`)
   تعتبرها إغفالاً آمناً لأن الشكل `EYE/OINTMENT` موضعي.
3. الدرجة الفعلية **15.36 ⟹ مقبول عبر «safe omission»**.

> **التقييم:** هذه المطابقة **غالباً صحيحة دوائياً** (AVAZIR 0.3% مرهم عين =
> نفس مادة CO_AVAZIR)، والبادئة `CO_` تُعامَل كـ token صامت `CO`. لكنها **حدّية**
> لأن الكود لا يفهم دلالة `CO_` (قد تكون شركة/تركيبة). ذُكِرت ضمن الأخطاء لأن
> المستخدم يريد يقيناً بأن `CO_` ليست فرقاً جوهرياً — وهذا صحيح هنا لكن غير
> مضمون كقاعدة عامة.

---

### ✅ الحالة 5 — `LILI FEMININE WASH 250ML` ⟵ `LILIOX 10 SACHETS` (الرفض صحيح، لكن السبب المُبلَّغ مضلِّل)

المستخدم لاحظ تناقضاً: البوت أعطى `not-orderable` برسالة «API candidates found
but none has an orderable storeProductId»، بينما المراجعة اليدوية سجّلت الصنف
كـ `not_matching` (لا مطابقة صحيحة).

**الأدلة القاطعة:**
1. في `data/input/tawreed_products.csv:34060`:
   `ليلوكس 10 اكياس,LILIOX 10 SACHETS,,79863.0,120.0` — **العمود الثالث
   (storeProductId) فارغ** (`,,`). أي أن `LILIOX` مرشح بلا `storeProductId`
   قابل للطلب.
2. تشغيل المطابقة فعلياً: الدرجة **4.07** فقط، والقرار **مرفوض**
   (`Arabic name missing marker for ML` عند غياب storeProductId، أو
   «none orderable» عبر `_has_only_non_orderable_candidates`
   في `tawreed_api_matching.py:165-172` قبل مرحلة التسجيل).
3. تعارض رمز/اسم إضافي: الرمز `79407` في `tawreed_products.csv:14077` مربوط بمنتج
   مختلف تماماً `NEVILOB AMLO 5/5 MG 30 TABS` — أي أن رمز الصنف نفسه ملغّم في
   بيانات المصدر.

> **الخلاصة:** رفض LILI **سلوك صحيح** (LILIOX منتج مختلف تماماً، ودرجته 4.07).
> المشكلة الوحيدة هي أن **الرسالة مضلِّلة**: تقول «لا يوجد storeProductId قابل
> للطلب» بينما السبب الحقيقي المركّب هو (أ) عدم وجود مطابقة دلالية أصلاً، و(ب)
> المرشح الوحيد `LILIOX` بلا storeProductId في بيانات المصدر. الرسالة تخفي أن
> «لا مطابقة صحيحة» هو السبب الأساسي، فتبدو كأنها خطأ توفّر لا خطأ مطابقة.

---

## 3. ترجيح الأسباب (Root Cause Ranking)

| # | السبب الجذري | الحالات المتأثرة | الترجيح | الدليل |
|---|---|---|---|---|
| **1** | درجة التداخل أحادية الاتجاه + `DISTINGUISHING_TOKENS` مفردات ثابتة صغيرة (9 كلمات) ⟹ لا التقاط للـ tokens المميّزة الإضافية | CAL MAG (JOINT), LIMITLESS (MAN), METHYL FOLATE (ORA) | **الأساسي** | درجات 22.12 / 20.62 / 19.10 مقبولة رغم فرق الهوية |
| **2** | فحص المُصنّع معطّل افتراضياً في الإنتاج (`enable_manufacturer_check=False`) | METHYL FOLATE | عالٍ | `config_models.py:62` + لا مفتاح في config.yaml |
| **3** | دالة استخراج الشركة معيبة (تعتبر آخر كلمة شركة) ⟹ رفض عشوائي لو فُعّلت | كل الحالات لو فُعّل الفحص | عالٍ (خطر) | مقارنات `MAG vs JOINT`, `AVAZIR vs OINT`, `WASH vs SACHETS` |
| **4** | رسالة `not-orderable` مضلِّلة تخلط «لا مطابقة» بـ «لا storeProductId» | LILI | متوسط | `tawreed_api_matching.py:119,165-172` + بيانات المصدر |
| **5** | عتبة الدرجة المتوسطة (12.0) متساهلة أمام أسماء متشابهة شكلياً مختلفة الهوية | LIMITLESS, METHYL FOLATE | متوسط | `matching_rules.py:109-120` |

---

## 4. الحلول الممكنة (كل الخيارات مع المفاضلة)

### الحل أ — تفعيل فحص المُصنّع كما هو (❌ مرفوض)
- **الفكرة:** ضبط `enable_manufacturer_check=True`.
- **لماذا يفشل:** الدالة تعتبر آخر كلمة شركة ⟹ رفض عشوائي واسع (أثبته التشغيل
  الفعلي: `MAG vs JOINT`, `WASH vs SACHETS`). **يكسر مطابقات صحيحة كثيرة.**

### الحل ب — إعادة تصميم فحص المُصنّع ليكون آمناً (✅ موصى به جزئياً)
- استخراج الشركة **فقط** من الحقل المنظَّم `companyName/supplierName` (موجود في
  المرشح عبر إثراء `tawreed_product_search.py:106-113`)، **لا** من ذيل الاسم.
- للاستعلام: مطابقة اسم الشركة مقابل **قائمة شركات معروفة** (whitelist من
  `tawreed_products.csv`) بدل «آخر كلمة».
- **الأثر:** يحلّ METHYL FOLATE بأمان دون رفض عشوائي.

### الحل ج — عقوبة/رفض على «token مميِّز إضافي في المرشح» بشكل عام (✅ الأقوى للسبب #1)
- توسيع منطق `extra_distinguishing`: أي token **غير عام وغير رقمي وغير
  موجود في الاستعلام** يُضاف في المرشح ويُعتبر «مميِّزاً» ⟹ عقوبة قوية أو رفض.
- يجب **قائمة استثناءات** للأشكال/الوحدات العامة (موجودة أصلاً في
  `_GENERIC_IDENTITY_TOKENS`) حتى لا يُعاقَب `TAB/CAPS/GM`.
- **الأثر:** يلتقط `JOINT`, `MAN`, `ORA` مباشرة. **هذا الحل يعالج الأعراض الثلاثة
  الأساسية دفعة واحدة.**
- **الخطر:** قد يرفض إغفالات آمنة (مثل `0.3%` في AVAZIR) — لذا يجب استثناء الـ
  tokens الرقمية والنسب المئوية والوحدات، والاعتماد على `_any_safe_omission`
  القائم.

### الحل د — رفع عتبة الدرجة المتوسطة أو جعل التداخل ثنائي الاتجاه (⚠️ مساعد)
- إضافة قياس عكسي (candidate → query) للتداخل، أو خفض قبول المتوسط عند وجود
  token إضافي مميِّز في المرشح.
- **الخطر:** رفع العتبة قد يكسر مطابقات صحيحة أخرى ⟹ يحتاج قياس واسع على بيانات
  فعلية قبل التطبيق.

### الحل هـ — تصحيح رسالة `not-orderable` (✅ منخفض الخطر)
- التمييز في الرسالة بين «لا مطابقة دلالية» و«مطابقة موجودة لكن بلا
  storeProductId»، حتى لا يظنّ المستخدم أنها خطأ توفّر.

### الحل و — توسيع شبكة المراجعة اليدوية (✅ شبكة أمان)
- أي رفض بسبب «token مميّز إضافي» أو «تعارض شركة» يجب أن يُنتج حالة ضمن
  `REVIEWABLE_STATUSES` (`order_run_artifact_rows.py:12-15`، فيها بالفعل
  `manufacturer-mismatch`) ليظهر في المراجعة بدل الإهمال الصامت.

---

## 5. الخطة الكاملة المرتّبة للحل (Milestones)

> **مبدأ حاكم:** كل بند دفاعي (يزيد الدقة/يوسّع المراجعة)، محافظ (يرفض عند
> تعارض مؤكد فقط)، قابل للضبط عبر Config، ومغطّى باختبار حماية.
> **بعد كل بند: `python3 -m pytest -q` كامل + `python3 tools/rule_audit.py`.**

### 🔴 M1 — إصلاح السبب الأساسي (#1): رفض/عقوبة الـ token المميّز الإضافي
1. في `matching_penalties.py`: إضافة دالة نقية `extra_meaningful_token_conflict`
   تكتشف tokens في المرشح غير موجودة في الاستعلام، **بعد** استبعاد:
   `_GENERIC_IDENTITY_TOKENS`، الأرقام، النسب المئوية، الوحدات.
2. ربطها بـ `compatibility_rejection_reason` أو `_check_rejections`
   (`product_matching_acceptance.py:354-385`) كسبب رفض/مراجعة **قابل للتعطيل عبر
   Config**.
3. **حقل Config جديد** في `config_models.py`: `reject_extra_brand_token: bool`
   + عتبة، موثّق في `config.yaml`.
4. **اختبار حماية** `test_product_matching.py`:
   - `CAL MAG` مقابل `CAL MAG JOINT` ⟹ مرفوض/مراجعة.
   - `LIMITLESS MILGA MAX` مقابل `LIMITLESS MAN MAX` ⟹ مرفوض/مراجعة.
   - مطابقات صحيحة قائمة (safe omissions) **لا تُكسر**.
- **بوابة التوقف:** كل اختبارات `test_product_matching.py` تمر + الحالتان
  ترفضان + لا انحدار في العدد الكلي (خط الأساس الحالي **414 passed**).

### 🔴 M2 — إصلاح فحص المُصنّع (#2 + #3) بأمان
1. إعادة تصميم `extract_manufacturer_from_name` لتعتمد **whitelist شركات** أو
   حقل منظَّم فقط، لا «آخر كلمة».
2. تفعيل `enable_manufacturer_check` **فقط بعد** إثبات أنه لا يُنتج رفضاً عشوائياً
   على عيّنة واسعة من `all_non_cosmotics_drug_all.csv`.
3. تحديث `tests/test_manufacturer_mismatch.py` ليتحقق أن الرفض بسبب **شركة
   حقيقية** لا مجرد `best_match is None` (التغطية الحالية خادعة — تمر حتى مع
   `MAG vs JOINT`).
- **بوابة التوقف:** METHYL FOLATE يُرفض بسبب `ORCHIDIA vs ORA` **فقط**، ولا يُرفض
  أي صنف بسبب مقارنة كلمة غير شركة.

### 🟠 M3 — شبكة المراجعة اليدوية (#4 من الحلول)
1. ضمان أن الرفض من M1/M2 يُنتج حالة ضمن `REVIEWABLE_STATUSES` (`manufacturer-mismatch`
   موجودة؛ تُضاف حالة/سبب للـ brand-token إن لزم).
2. اختبار في `tests/core/ordering/test_order_run_artifacts.py`.

### 🟡 M4 — تصحيح رسالة `not-orderable` (#5)
1. في `tawreed_api_matching.py` + `tawreed_api_flow_matching.py`: تمييز الرسالة بين
   «لا مطابقة دلالية» و«لا storeProductId».
2. اختبار في `tests/tawreed/api/`.

### 🟡 M5 — المراقبة والتوثيق
1. حقل تشخيصي في صف الـartifact يبيّن الـ token المميّز/الشركة وقرار الفحص.

---

## 6. بوابة التحقق الإلزامية (Verification Gate)

**البيئة (لإتاحة جمع كل الاختبارات):**
```
pip install --break-system-packages python-dotenv playwright psycopg2-binary
```
(بدون هذه الحزم تفشل 16 اختبار collection — psycopg2/playwright/dotenv.)

**خط الأساس الملتقَط الآن (نظيف):**
```
python3 -m pytest -q --ignore=tools
⟹ 414 passed, 20 skipped, 117 subtests passed
```

**بعد كل بند:**
1. الاختبار المستهدف للبند.
2. `python3 -m pytest -q --ignore=tools` (يجب ألا يقلّ عن 414 ناجحاً).
3. `python3 tools/rule_audit.py` (يبقى `rule_audit_ok`، لا زيادة مخالفات).

**معيار القبول النهائي:**
- `CAL MAG 30TAB` لم يعد يُطابَق تلقائياً بـ `CAL MAG JOINT 30 TAB`.
- `LIMITLESS MILGA MAX` لم يعد يُطابَق بـ `LIMITLESS MAN MAX`.
- `METHYL FOLATE ... ORCHIDIA` يُرفض بسبب `ORCHIDIA vs ORA` تحديداً ويظهر في
  المراجعة.
- لا رفض عشوائي بسبب كلمة غير شركة.
- رسالة LILI توضّح السبب الحقيقي.
- لا انحدار مقابل خط الأساس (414).

---

## 7. مخاطر وملاحظات (Risks & Notes)

1. **خطر كسر الإغفالات الآمنة:** حلّ M1 يجب أن يستثني الأرقام/النسب/الوحدات
   ويعتمد `_any_safe_omission` القائم، وإلا سيكسر AVAZIR (0.3%) وغيره.
2. **`ORA` غامضة:** قد تكون اختصار «oral» لا شركة ⟹ الاعتماد على `companyName`
   المنظَّم أدق من ذيل الاسم.
3. **بيانات المصدر ملغّمة:** رمز `79407` مربوط باسمين مختلفين
   (`LILI` في الطلب، `NEVILOB` في المنتجات) ⟹ أي إصلاح مطابقة لا يحلّ فساد
   البيانات نفسه؛ يلزم تدقيق منفصل لملفات الإدخال.
4. **التغطية الاختبارية الحالية خادعة:** `test_manufacturer_mismatch.py` يمرّ حتى
   مع مقارنات هراء لأنه يفحص `best_match is None` فقط ⟹ يجب تشديده في M2.
5. **لا تغيير سلوكي في الحالات الصحيحة:** كل بند خلف مفتاح Config قابل للإيقاف
   ومغطّى باختبار حماية، التزاماً بـ `project_guidelines.md` و`starting_prompt.md`.
