# 5 — الفرضيات التي تم نفيها

هذا الملف مهم حتى لا يتم علاج العرض الخطأ وترك السبب الحقيقي.

## الفرضية 1: Tawreed لا يحتوي المنتج الصحيح

الحكم: منفية.

الدليل:

```csv
ريتشي بانثينول ادفانس كريم,U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM,2685228.0,,110.0
```

السطر موجود في:

```
data/input/tawreed_products.csv
```

كما أن trace أظهر مرشحاً قريباً جداً بالاسم:

```
U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM
```

إذن ليست مشكلة "الصنف غير موجود".

## الفرضية 2: البحث لم يرجع أي candidates

الحكم: منفية.

الدليل: `order_result_summary` و`manual_review_candidates_*.jsonl` يحتويان candidates كثيرة، منها:

```
U RICHI FACIAL WASH FOR NORMAL SKIN 50 ML
U RICHI FACIAL WASH FOR OILY SKIN 50 ML
U RICHI PANTHENOL CREAM 50 GM
U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM
```

إذن المشكلة ليست في عدم وجود نتائج، بل في تصنيف/قبول النتائج.

## الفرضية 3: الـ Saved Correction غير محفوظ نهائياً

الحكم: غير مثبتة كسبب أساسي، ولم يتم التحقق من قاعدة CockroachDB الحية في هذه المراجعة.

المستخدم ذكر أن row موجود في Saved Corrections:

```
235
FALSE
91167
U RICHI PANTHENOL ADVANCE CREAM GEL 50M
20260629_1429
needs_correction
```

منطق الكود يدعم هذا النوع (`needs_correction`) ويستخدم `correct_query` في `manual_review_queries()` إذا كان الحقل محفوظاً فعلاً في row.

لكن حتى لو كان محفوظاً بشكل صحيح، لن يفرض match لأنه `approved=False`، وسيظل يمر عبر `explain_best_product_match()` الذي يرفض CREAM/GEL.

إذن نقص الحفظ ليس السبب الأرجح. السبب الأقوى أن نوع decision لا يتجاوز bug الرفض.

## الفرضية 4: سبب المشكلة فقط هو `50M` بدل `50 GM`

الحكم: سبب مساعد لكنه ليس السبب الأساسي.

لو كان `50M` هو السبب الوحيد، لما ظهر المنتج الصحيح/القريب في trace. لكنه ظهر وحصل على:

```
numeric_overlap = 1.0
sequence_score  = 0.987654
overlap_score   = 0.9625
```

هذا يعني أن النظام فهمه بدرجة كافية للوصول للمنتج. الرفض جاء لاحقاً بسبب:

```
Semantic token conflict: CREAM vs GEL, GEL vs CREAM
```

## الفرضية 5: سبب المشكلة أن المنتج الصحيح غير orderable

الحكم: منفية جزئياً.

في الكتالوج المحلي السطر يحتوي `2685228.0`، لكن الكتالوج وحده لا يثبت orderability. الدليل الأقوى أن trace يحتوي المرشح القريب:

```
storeProductId = 2442366
orderable      = True
```

إذن على الأقل candidate قريب جداً كان orderable. الرفض لم يكن بسبب غياب `storeProductId`.

## الفرضية 6: المشكلة في صفحة Streamlit فقط

الحكم: منفية كسبب كامل.

واجهة Streamlit بالفعل تعرض JSONL قديم، وهذا يفسر الخيارات الخاطئة، لكنها ليست سبب فشل المطابقة الأصلي. الفشل الأصلي حدث في `require_api_match()` و`explain_best_product_match()` قبل كتابة artifacts.

إذن لدينا مشكلتان مرتبطتان:

1. Matching engine يرفض candidate الصحيح.
2. Manual Review UI يعرض Top 5 من أثر هذا الرفض ولا يعيد البحث بعد التصحيح.

## الفرضية 7: AI matching هو من رفض المنتج

الحكم: غير مرجحة.

الرفض الظاهر في trace هو deterministic matching reason من `matching_penalties.py`:

```
Semantic token conflict: CREAM vs GEL, GEL vs CREAM
```

وليس رسالة من AI review. لذلك العلاج يجب أن يبدأ من deterministic matching rules.
