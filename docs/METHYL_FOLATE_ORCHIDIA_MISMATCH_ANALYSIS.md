# تحليل مشكلة METHYL FOLATE ORCHIDIA مقابل ORA

> التاريخ: 2026-07-04  
> الصنف: `83165 - METHYL FOLATE 30 CAP ORCHIDIA`  
> المطابقة الخاطئة: `METHYL FOLATE ORA 30 CAPS` / `ميثيل فولات اورا 30 كبسول`  
> النتيجة المرصودة في التشغيلات: `matched-only` في آخر تشغيل آمن، و`added-to-cart` في تشغيلات سابقة بسبب قرار محفوظ.  
> نطاق هذا الملف: تشخيص تفصيلي بالأدلة، ترجيح الأسباب، كل الحلول الممكنة، وخطة تنفيذ مرتبة. لم أغير كود الإنتاج في هذه الخطوة.

## 1. الخلاصة التنفيذية

المشكلة ليست سبباً واحداً فقط. يوجد مساران مستقلان يجعلان ORA يفوز:

1. **مسار القرار المحفوظ**: توجد مطابقة محفوظة للصنف 83165 إلى `METHYL FOLATE ORA 30 CAPS`. عند وجود هذا القرار، الكود يطبقه قبل خوارزمية المطابقة ويمنحه score = `999.0`، لذلك يتم تجاوز كل قواعد scoring والرفض. هذا هو السبب الأكثر ترجيحاً لحالات `added-to-cart` القديمة.
2. **مسار المطابقة الحتمية**: عند عدم استخدام القرار المحفوظ، الخوارزمية نفسها تقبل ORA بدرجة `19.103704` لأن فحص الشركة معطل، ومفتاح `reject_extra_brand_token` الموجود في `state/config.yaml` غير مقروء من نموذج الإعدادات وغير منفذ في منطق المطابقة.

الأخطر أن المرشح الصحيح موجود في آخر تشغيل:

`METHYL FOLATE (ORCHIDIA) 30 CAPS`

لكنه رُفض بستة صفوف متتالية بسبب:

`Semantic token conflict: different_brand`

بينما المرشح الخاطئ ORA قُبل:

`Accepted best candidate because No extra numeric tokens.`

إذن العلاج الصحيح ليس "تفعيل فحص الشركة" فقط. يجب معالجة أربعة أشياء معاً: تنظيف القرار المحفوظ، إصلاح رفض ORCHIDIA الصحيح، تنفيذ/قراءة مفتاح extra brand token، ثم حماية auto-save/manual-review من إعادة تكوين الخطأ.

## 2. الأدلة التي تم فحصها

### 2.1 إعادة إنتاج القرار الحالي من الكود

تشغيل `explain_best_product_match` مباشرة على الحالة أعطى:

```text
CFG None
best True
reason Accepted best candidate because No extra numeric tokens.
score 19.103703703703705
accepted True

CFG MatchingConfig(enable_manufacturer_check=True)
best False
reason Manufacturer conflict: ORCHIDIA vs ORA
```

الاستنتاج: الكود الحالي قادر على رفض ORA فقط إذا فُعّل `enable_manufacturer_check` صراحة في الكود. لكنه افتراضياً `False` في [config_models.py](../src/core/config/config_models.py:62).

### 2.2 آخر تشغيل آمن بتاريخ 2026-07-04

من:

`artifacts/order/wardany/20260704_1356/order_item_summary_20260704_1356.csv`

صف الصنف 83165:

```text
item_name = METHYL FOLATE 30 CAP ORCHIDIA
status = matched-only
matched_query = METHYL FOLATE 30 CAP ORCHIDIA
deterministic_score = 19.103704
matched_product_name_en = METHYL FOLATE ORA 30 CAPS
matched_store_product_id = 2627798
tie_break_reason = Accepted best candidate because No extra numeric tokens.
query_manufacturer = ORCHIDIA
candidate_manufacturer = blank
manufacturer_check_decision = unknown
manual_review_required = False
```

هذا يثبت أن النظام قبل ORA حتمياً، ولم يرسله للمراجعة اليدوية.

### 2.3 المرشح الصحيح كان موجوداً لكنه رُفض

من:

`artifacts/order/wardany/20260704_1356/match_only_summary_20260704_1356.csv`

أفضل المرشحين للصنف 83165:

| rank | accepted | product | score | overlap | reason |
|---|---:|---|---:|---:|---|
| 1 | False | `METHYL FOLATE (ORCHIDIA) 30 CAPS` | 21.128814 | 0.94 | `Semantic token conflict: different_brand` |
| 2 | False | `METHYL FOLATE (ORCHIDIA) 30 CAPS` | 21.128814 | 0.94 | `Semantic token conflict: different_brand` |
| 3 | False | `METHYL FOLATE (ORCHIDIA) 30 CAPS` | 21.128814 | 0.94 | `Semantic token conflict: different_brand` |
| 4 | False | `METHYL FOLATE (ORCHIDIA) 30 CAPS` | 21.128814 | 0.94 | `Semantic token conflict: different_brand` |
| 5 | False | `METHYL FOLATE (ORCHIDIA) 30 CAPS` | 19.128814 | 0.94 | `Semantic token conflict: different_brand` |
| 6 | False | `METHYL FOLATE (ORCHIDIA) 30 CAPS` | 19.128814 | 0.94 | `Semantic token conflict: different_brand` |
| 7 | True | `METHYL FOLATE ORA 30 CAPS` | 19.103704 | 0.74 | accepted |

هذا أهم دليل في التحقيق: النظام لا يفشل فقط في رفض ORA؛ هو أيضاً يرفض ORCHIDIA الصحيح.

### 2.4 تحليل parser للمرشحين

تشغيل `parse_drug` و`components_match` أعطى:

```text
query brand = METHYLFOLATE
orchidia_candidate brand = METHYLFOLATEORCHIDIA
ora_candidate brand = METHYLFOLATEORA

query vs ORCHIDIA candidate = (False, 'different_brand')
query vs ORA candidate = (True, 'ok')
```

السبب: `parse_drug('METHYL FOLATE 30 CAP ORCHIDIA')` يتوقف عند الرقم `30`، فيجعل brand = `METHYLFOLATE`. أما `parse_drug('METHYL FOLATE (ORCHIDIA) 30 CAPS')` فيرى `ORCHIDIA` قبل الرقم بعد normalization، فيجعل brand = `METHYLFOLATEORCHIDIA`. ثم `_brand_match_check` في [normalizer_matching_brand.py](../src/core/drug_matching/normalization/normalizer_matching_brand.py:8) يعتبرهما مختلفين.

### 2.5 القرار المحفوظ يفسر added-to-cart

من تشغيلات سابقة:

`artifacts/order/wardany/20260702_1104/order_item_summary_20260702_1104.csv`

```text
status = added-to-cart
matched_query = METHYL FOLATE ORA 30 CAPS
deterministic_score = 999.0
tie_break_reason = Approved by saved manual review (ID match).
```

ومن:

`artifacts/order/wardany/20260624_1451/order_item_summary_20260624_1451.csv`

```text
status = added-to-cart
matched_query = METHYL FOLATE ORA 30 CAPS
deterministic_score = 999.0
tie_break_reason = Approved by saved manual review (Name match).
```

كما يوجد صف في `docs/saved_corrected_items(2).csv`:

```text
83165,METHYL FOLATE 30 CAP ORCHIDIA,auto_matched,METHYL FOLATE ORA 30 CAPS,ميثيل فولات اورا 30 كبسول
```

مسار الكود:

- `manual_review_match` في [manual_review_runtime.py](../src/core/manual_review/manual_review_runtime.py:108) يبحث عن قرار محفوظ.
- `_find_manual_review_match` في [manual_review_helpers.py](../src/core/manual_review/manual_review_helpers.py:63) يطابق بالـ ID أو بالاسم.
- عند التطابق، يرجع `MatchDecision` بدرجة `999.0` وسبب `Approved by saved manual review`.
- `_api_match_decision` في [tawreed_api_matching.py](../src/tawreed/api/tawreed_api_matching.py:73) يستدعي `manual_review_match` قبل `explain_best_product_match`.

هذا يعني أن أي إصلاح في scoring لن يعمل إذا بقي القرار المحفوظ الخاطئ موجوداً.

## 3. لماذا فشلت خطة MANUFACTURER_MISMATCH_FIX_PLAN.md السابقة؟

الخطة السابقة نفذت أجزاء حقيقية:

- [manufacturer_identity.py](../src/core/identity/manufacturer_identity.py:21) لاستخراج الشركة.
- [_candidate_manufacturer_rejection](../src/core/matching/product_matching_acceptance.py:318) لرفض التعارض.
- `tests/test_manufacturer_mismatch.py`.
- حقول artifact مثل `query_manufacturer` و`manufacturer_check_decision`.

لكنها لم تحل التشغيل الفعلي للأسباب التالية:

1. `enable_manufacturer_check` افتراضياً `False` في [config_models.py](../src/core/config/config_models.py:62).
2. `build_matching_config` لا يقرأ `enable_manufacturer_check` ولا `manufacturer_match_threshold` من YAML، لأن `bool_keys` في [config_factory.py](../src/core/config/config_factory.py:65) لا يحتوي المفتاح، وقائمة floats في [config_factory.py](../src/core/config/config_factory.py:80) لا تحتوي threshold.
3. `state/config.yaml` لا يحتوي `enable_manufacturer_check` أصلاً.
4. `state/config.yaml` يحتوي `reject_extra_brand_token: true` في [state/config.yaml](../state/config.yaml:84)، لكن `MatchingConfig` لا يحتوي هذا الحقل، و`config_factory` لا يقرأه، ولا توجد قاعدة تستخدمه في `matching_penalties.py`.
5. الاختبار الحالي في `tests/test_manufacturer_mismatch.py` يمرر `MatchingConfig(enable_manufacturer_check=True)` يدوياً، لذلك لا يختبر إعداد الإنتاج.
6. القرار المحفوظ manual review يسبق خوارزمية المطابقة، وبالتالي لا يتأثر بفحص الشركة أصلاً.
7. تفعيل فحص الشركة كما هو قد يسبب رفضاً عشوائياً، لأن `extract_manufacturer_from_name` يأخذ آخر token غير عام كأنه شركة. هذا صحيح صدفة في `ORCHIDIA`، لكنه خطر في أسماء كثيرة.

## 4. ترتيب الأسباب المحتملة مع الترجيح

| الترتيب | السبب | الترجيح | لماذا |
|---:|---|---:|---|
| 1 | قرار محفوظ خاطئ يفرض ORA بدرجة 999 | 95% لحالات `added-to-cart` | الأرتيفاكت تعرض `Approved by saved manual review (ID/Name match)` وscore `999.0` |
| 2 | فحص الشركة معطل وغير مقروء من YAML | 90% لمسار المطابقة الحتمية | الافتراضي `False`، وإعادة الإنتاج تقبل ORA بدون التفعيل وترفضه مع التفعيل |
| 3 | المرشح الصحيح ORCHIDIA يرفض بسبب `different_brand` | 90% | آخر تشغيل يظهر 6 مرشحين ORCHIDIA مرفوضين رغم score أعلى من ORA |
| 4 | `reject_extra_brand_token` إعداد وهمي غير منفذ | 85% | موجود في `state/config.yaml` فقط، ولا يوجد في `MatchingConfig` أو `config_factory` |
| 5 | auto-save يحول الخطأ إلى ذاكرة دائمة | 80% | `enable_auto_save_verified_match=True` و`_auto_save_verified_match` يحفظ أي match لا يحتاج review كـ `auto_matched` |
| 6 | اختبارات manufacturer تغطي المسار السهل فقط | 75% | تختبر config مفعّل يدوياً ولا تختبر default/config YAML/manual review |
| 7 | `companyName` في نتائج Tawreed ليس manufacturer حقيقياً | 70% | الأرتيفاكت تعرض `companyName` كمخزن/شركة توزيع مثل `شركه تيم فارما`، وليس ORA/ORCHIDIA |
| 8 | item code 83165 ملتبس مع productId آخر في catalog | 25% | `data/input/tawreed_products.csv` فيه `83165` مرتبط بـ `LECA 20 PIECES`، لكن البحث الحالي لا يستخدم الكود كاستعلام، لذا ليس السبب الأساسي |

## 5. شرح مسار الخطأ خطوة بخطوة

### 5.1 عندما يوجد قرار محفوظ

1. يبدأ `require_api_match`.
2. يتم تحميل قرار manual review للصنف.
3. `manual_review_queries` يضع `METHYL FOLATE ORA 30 CAPS` كاستعلام مفضل.
4. نتائج Tawreed تحتوي ORA.
5. `manual_review_match` يجد ID أو name مطابقاً للقرار المحفوظ.
6. يرجع `SearchMatch(score=999.0)`.
7. `_is_saved_manual_review_match` يعتبره حاسماً.
8. يتم add-to-cart إذا التشغيل ليس match-only.

هذا هو مسار `added-to-cart`.

### 5.2 عندما لا يوجد قرار محفوظ

1. `explain_best_product_match` يبني diagnostics لكل مرشح.
2. مرشحو `METHYL FOLATE (ORCHIDIA) 30 CAPS` يحصلون على score أعلى (`21.128814`) لكن يرفضون من `_candidate_component_rejection`.
3. `components_match` يرجع `different_brand`.
4. مرشح `METHYL FOLATE ORA 30 CAPS` لا يحصل على `different_brand`.
5. لا يوجد `enable_manufacturer_check`.
6. لا يوجد `reject_extra_brand_token`.
7. لا توجد أرقام زائدة، فيقبل بـ `No extra numeric tokens`.
8. لا يدخل manual review لأن الحالة `matched-only` أو `added-to-cart` وليست ضمن الحالات القابلة للمراجعة.

## 6. الحلول الممكنة

### الحل A: حذف القرار المحفوظ الخاطئ فقط

المطلوب:

- حذف/تعديل قرار 83165 من `manual_review_decisions`.
- إزالة أو تعديل أي CSV import مثل `docs/saved_corrected_items(2).csv` إذا كان سيعاد استيراده.

المميزات:

- أسرع حل لحالات `added-to-cart`.
- يمنع score 999 من فرض ORA.

العيوب:

- لا يحل قبول ORA في المسار الحتمي.
- قد يعود الخطأ عبر auto-save إذا قبلت الخوارزمية ORA مرة أخرى.

الحكم: ضروري فوراً، لكنه ليس كافياً.

### الحل B: تفعيل `enable_manufacturer_check` كما هو

المطلوب:

- إضافة المفتاح إلى `state/config.yaml`.
- تعديل `config_factory.py` ليقرأ `enable_manufacturer_check` و`manufacturer_match_threshold`.

المميزات:

- يرفض الحالة المباشرة `ORCHIDIA vs ORA`.

العيوب:

- خطر false positives لأن استخراج الشركة من اسم الصنف يعتمد على آخر token.
- `companyName` في Tawreed هو غالباً مخزن/مورد وليس manufacturer.
- لا يصلح رفض المرشح الصحيح ORCHIDIA.
- لا يمنع القرار المحفوظ من التجاوز.

الحكم: لا ينفذ وحده.

### الحل C: إصلاح parsing للـ manufacturer داخل اسم المنتج

المطلوب:

- اعتبار كلمات داخل أقواس مثل `(ORCHIDIA)` أو tail manufacturer tokens كـ manufacturer/descriptor، لا كجزء من brand الأساسي.
- جعل `METHYL FOLATE 30 CAP ORCHIDIA` و`METHYL FOLATE (ORCHIDIA) 30 CAPS` متوافقين.
- جعل `METHYL FOLATE ORA 30 CAPS` غير متوافق عندما الطلب يذكر ORCHIDIA.

المميزات:

- يعالج السبب الذي جعل المرشح الصحيح يخسر.
- يرفع دقة matching بدلاً من مجرد رفض ORA.

العيوب:

- يحتاج اختبارات كثيرة حتى لا يكسر أسماء منتجات يكون tail token فيها فعلاً جزءاً من brand.

الحكم: هذا جزء أساسي من الحل الصحيح.

### الحل D: تنفيذ `reject_extra_brand_token`

المطلوب:

- إضافة الحقل إلى `MatchingConfig`.
- قراءته من `config_factory.py`.
- تطبيقه في `matching_penalties.py` أو `_check_rejections`.
- استثناء الأرقام، الوحدات، forms، وتركيبات safe omission.

المميزات:

- يعالج ORA كـ token إضافي مميز غير مطلوب.
- يفيد حالات مشابهة مثل `CAL MAG` مقابل `CAL MAG JOINT` و`LIMITLESS MILGA` مقابل `LIMITLESS MAN`.

العيوب:

- إذا طبق بعنف قد يرفض إضافات آمنة.
- يحتاج whitelist/allowlist للـ generic tokens.

الحكم: مطلوب، لكن خلف config ومع اختبارات regression.

### الحل E: حماية manual review saved matches بفحص أمان

المطلوب:

- قبل قبول `manual_review_match` بدرجة 999، شغّل safety validation:
  - هل المنتج المحفوظ ما زال يطابق item الحالي؟
  - هل يوجد manufacturer/brand conflict واضح؟
  - هل تطابق الاسم المحفوظ تغير إلى منتج مختلف؟
- إذا فشل، لا تضفه للسلة، بل حوله إلى manual review.

المميزات:

- يمنع أي قرار قديم خاطئ من تجاوز قواعد السلامة.
- يحمي النظام من قرارات `auto_matched` القديمة.

العيوب:

- قد يعرقل قرارات بشرية صحيحة إذا كان الفحص صارماً جداً.

الحكم: ضروري، ويفضل التفريق بين `auto_matched` و`approved_match`: القرار البشري أقوى، لكن لا يجب أن يتجاوز تعارضاً دوائياً خطيراً بلا مراجعة.

### الحل F: وقف/تقييد auto-save

المطلوب:

- لا تحفظ `auto_matched` إلا إذا:
  - لا يوجد conflict.
  - confidence/score أعلى من threshold.
  - لا يوجد token مميز إضافي.
  - ليس هناك candidate مرفوض أعلى score بسبب سبب قابل للمراجعة مثل `different_brand`.
- منع auto-save من كتابة قرار إذا كان match جاء من استعلام قصير أو من مرشح منخفض overlap.

المميزات:

- يمنع تحويل الأخطاء العابرة إلى قرارات دائمة.

العيوب:

- يقلل التعلم التلقائي.

الحكم: مهم جداً بعد تنظيف القرار الخاطئ.

### الحل G: إدخال الحالة في manual review بدلاً من matched

المطلوب:

- إذا رفض أفضل مرشح بسبب `different_brand` وكان هناك مرشح آخر مقبول أقل score، لا تقبل الأقل مباشرة.
- أضف سبب review مثل `higher_scoring_brand_conflict`.
- أو على الأقل إذا كان أفضل مرشح مرفوض أعلى من الفائز بفارق صغير/كبير، ارفع الحالة للمراجعة.

المميزات:

- يمنع سيناريو "المرشح الصحيح رُفض، فقبلنا المرشح الأقل".

العيوب:

- يزيد عدد manual review.

الحكم: شبكة أمان مهمة.

## 7. الخطة المرتبة للحل

### M0 - إيقاف النزيف فوراً

1. استخراج قرار manual review الحالي للصنف 83165 من قاعدة `manual_review_decisions`.
2. إن كان يشير إلى ORA، حذفه أو تحويله إلى `not_matching` للـ `storeProductId` الخاص بـ ORA.
3. تعطيل auto-save مؤقتاً أو على الأقل عدم auto-save لهذا الصنف حتى يكتمل الإصلاح.
4. تشغيل match-only للصنف 83165 للتأكد أنه لا يستخدم score 999.

معيار النجاح:

- لا يظهر `Approved by saved manual review` للصنف 83165.
- لا يتم add-to-cart لـ ORA.

### M1 - اختبارات فاشلة أولاً

أضف اختبارات تثبت الفشل الحالي:

1. default config لا يجب أن يقبل `METHYL FOLATE ORA 30 CAPS` لـ ORCHIDIA.
2. `METHYL FOLATE (ORCHIDIA) 30 CAPS` يجب أن يفوز على ORA.
3. `reject_extra_brand_token` من YAML يجب أن يصل إلى `MatchingConfig`.
4. saved `auto_matched` خاطئ يجب أن يفشل safety validation ولا يفرض score 999.
5. auto-save لا يحفظ ORA عندما الطلب يحتوي ORCHIDIA.

معيار النجاح:

- الاختبارات تفشل قبل الإصلاح وتنجح بعده.

### M2 - إصلاح config

1. إضافة `reject_extra_brand_token` إلى `MatchingConfig`.
2. إضافة `enable_manufacturer_check` و`manufacturer_match_threshold` إلى قراءة `config_factory.py`.
3. تحديث `config.example.yaml`.
4. اختبار أن `state/config.yaml` ينتج config يحتوي القيم المتوقعة.

معيار النجاح:

- لا توجد مفاتيح matching في YAML بلا تأثير.

### M3 - إصلاح ORCHIDIA كـ manufacturer وليس brand

1. تعديل parsing أو component matching بحيث لا يعتبر `(ORCHIDIA)` جزءاً من brand الأساسي إذا ظهر كلاحقة manufacturer.
2. إضافة known manufacturer extraction آمن من:
   - أقواس الاسم الإنجليزي.
   - tail token معروف من item name.
   - قائمة شركات مستخرجة/مضبوطة، لا "آخر كلمة" عشوائياً.
3. اختبار:
   - `METHYL FOLATE 30 CAP ORCHIDIA` يطابق `METHYL FOLATE (ORCHIDIA) 30 CAPS`.
   - لا يطابق `METHYL FOLATE ORA 30 CAPS`.

معيار النجاح:

- المرشح الصحيح ORCHIDIA accepted، وORA rejected أو manual review.

### M4 - تنفيذ extra brand token rejection

1. تطبيق `reject_extra_brand_token` في طبقة matching لا في Tawreed integration.
2. استثناء generic/form/unit/numeric tokens.
3. اختبار حالات:
   - `CAL MAG 30TAB` لا يقبل `CAL MAG JOINT 30 TAB`.
   - `LIMITLESS MILGA MAX` لا يقبل `LIMITLESS MAN MAX`.
   - safe omission الموجودة في `tests/test_product_matching.py` لا تنكسر.

معيار النجاح:

- تقليل false positives بدون كسر safe omissions.

### M5 - حماية manual review والـ auto-save

1. إضافة safety validation قبل forced manual review match.
2. إذا القرار `auto_matched` وفشل validation، يعاد إلى manual review.
3. إذا القرار `approved_match` وفشل validation، يرفع تحذير/manual review و add-to-cart.
4. تعديل `_auto_save_verified_match` حتى لا يحفظ matches عليها conflict أو candidate أعلى مرفوض بسبب conflict.

معيار النجاح:

- لا يستطيع قرار ORA محفوظ أن يتجاوز القواعد.
- لا يعاد حفظ ORA تلقائياً.

### M6 - artifacts ووضوح السبب

1. ملء `candidate_manufacturer` بصورة مفيدة، أو عدم الادعاء بأنه manufacturer إذا كان `companyName` مخزناً.
2. إضافة حقول:
   - `saved_manual_review_decision`
   - `saved_manual_review_safety_decision`
   - `higher_scoring_rejected_candidate`
   - `higher_scoring_rejection_reason`
3. جعل manual review يظهر عند `manufacturer-mismatch` و`brand-token-mismatch`.

معيار النجاح:

- عند التدقيق، يظهر لماذا لم يضف النظام الصنف أو لماذا طلب مراجعة.

## 8. أوامر التحقق المطلوبة بعد التنفيذ

بعد كل milestone كودي:

```powershell
python -m pytest tests\test_manufacturer_mismatch.py tests\test_product_matching.py -q
python -m pytest tests\core\manual_review tests\core\ordering tests\tawreed\matching tests\tawreed\api -q
python -m pytest -q --ignore=tools
python tools\rule_audit.py
```

واختبار تشغيلي آمن للصنف فقط:

```powershell
python run.py order --profile wardany --excel <file-with-only-83165.xlsx> --match-only --execution-mode auto
```

يجب أن تكون النتيجة واحدة من:

- `matched-only` مع `METHYL FOLATE (ORCHIDIA) 30 CAPS`.
- أو `manual-review-required`.
- وليس `METHYL FOLATE ORA 30 CAPS`.

## 9. ما لا يجب فعله

1. لا تكتف بتغيير `state/config.yaml` إلى `enable_manufacturer_check: true`.
2. لا تثق في `companyName` كـ manufacturer؛ في الأرتيفاكت هو غالباً اسم مخزن/مورد.
3. لا تترك قرار ORA المحفوظ في قاعدة manual review.
4. لا تترك `enable_auto_save_verified_match` يحفظ matches منخفضة الأمان.
5. لا تجعل extra token rejection عاماً بلا استثناءات، لأنه قد يكسر safe omissions.

## 10. القرار النهائي المقترح

الأولوية العملية:

1. حذف/تحييد قرار ORA المحفوظ للصنف 83165 فوراً.
2. إصلاح رفض `METHYL FOLATE (ORCHIDIA) 30 CAPS` الصحيح.
3. تنفيذ قراءة وتطبيق `reject_extra_brand_token`.
4. حماية manual review forced matches وauto-save.
5. بعدها فقط تفعيل manufacturer check بصورة آمنة ومدعومة بقائمة/استخراج موثوق.

بهذا نغلق المسارين: مسار الذاكرة المحفوظة ومسار المطابقة الحتمية.
