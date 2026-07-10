# 1 — ملخص المشكلة والأعراض

## وصف المشكلة المختصر

الصنف المطلوب (من ملف Excel):
```
code  = 91167
name  = U RICHI PANTHENOL ADVANCE CREAM GEL 50M   (لاحظ "50M" بدون GM)
qty   = 1 حسب وصف المشكلة، وظهر في artifact الخاص بـ run 20260629_1429 كـ 7
```

المنتج الصحيح الذي يجب أن يُطابِق (موجود في كتالوج Tawreed `data/input/tawreed_products.csv`):
```
name_ar = ريتشي بانثينول ادفانس كريم
name_en = U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM
id      = 2685228
price   = 110.0
```

نتيجة تشغيل `order` (run `20260629_1429` على profile `wardany`):
```
status        = not-orderable   (مُسجّلة في summary بسبب عدم وجود match حاسم)
final_reason  = "No decisive match found for 'U RICHI PANTHENOL ADVANCE CREAM GEL 50M' after 11 queries."
best_match    = لا يوجد match مقبول؛ والـ summary يعرض أعلى candidate تشخيصي فقط
queries tried = 11 في artifact 20260629_1429، بينما وصف المستخدم ذكر 12 في تشغيل آخر أو ملخص آخر
```

## الأعراض الثلاثة المرصودة بواسطة المستخدم

### العرض 1: "No decisive match found" — لا توجد نتيجة مطابقة

رغم أن المنشأة نفسها (U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM) موجودة فعلياً في نتائج
بحث Tawreed (مُثبَت من `matching_trace_20260629_1429.csv`، السطر رقم 9)، تم رفضها واعتبرها
النظام "no decisive match". ظهر أفضل مرشّح من حيث الـ score اسمه:
`U RICHI FACIAL WASH FOR NORMAL SKIN 50 ML` — وهو منتج **مختلف تماماً** (غسول للوجه).

### العرض 2: التسمية الصحيحة موجودة في Saved Corrections (Manual Review Store)

الـ saved decision الذي قدّمه المستخدم مسبقاً كـ `needs_correction`:
```
item_code        = 91167
item_name        = U RICHI PANTHENOL ADVANCE CREAM GEL 50M
manual_decision  = needs_correction
correct_query    = (مفترض) U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM
```
هذا الـ correction يُخزَّن في CockroachDB جدول `manual_review_decisions`.
المنطق (في `manual_review_queries`) يفترض أن يستخدم `correct_query` كأول query بحث في
التشغيل التالي، وهذا يرفع فرصة العثور على المنتج الصحيح، لكنه لا يفرض قبول النتيجة لأن
`needs_correction` ليس `approved_match`.

### العرض 3: الخيارات المعروضة في صفحة Manual Review كلها خاطئة

تظهر الخيارات التالية في تبويب Manual Review لـ run `20260629_1429`:
```
[1] U RICHI FACIAL WASH FOR NORMAL SKIN 50 ML  | ... | ✅
[2] U RICHI FACIAL WASH FOR OILY SKIN 50 ML    | ... | ✅
[3] U RICHI U RICHI BODY OIL 50 ML            | None | ⚠️ Unorderable
[4] CALCITONIUM 50 I.U. / ML 5 AMPS           | ... | ✅
[5] U RICHI PANTHENOL CREAM 50 GM              | ... | ✅
```

المنتج الصحيح (U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM) **لا يظهر** في القائمة القديمة، رغم أن
المستخدم ذكر أنه قدّم الاسم الصحيح في Saved Corrections. هذا أدى إلى انطباع بأن "المراجعة اليدوية تتجاهل التصحيح".

## الأرقام المرجعية

- run_id المعني: `20260629_1429` (والأحدث `20260709_1201` يعاني نفس المشكلة).
- item_code: `91167`.
- store_product_id الصحيح (من الكتالوج): `2685228`.
- store_product_id المنتج المُلتبِس الذي يظهر في نتائج البحث ونفس الاسم تقريباً: `2442366`.
- store_product_id لـ "U RICHI PANTHENOL **CREAM GEL** 50 GM" (بدون ADVANCE): `2670885`.

## لماذا المشكلة خطيرة

1. المنتج الصحيح موجود فعلاً في الكتالوج وله سعر، لكن النظام يرفض المرشح القريب في نتائج البحث.
2. المستخدم قدّم التصحيح في saved corrections، لكنه لا يغيّر خيارات
   المراجعة تُحمَل من ملف JSONL **قديم** مكتوب أثناء التشغيل الأصلي وليس من نتائج بحث مباشر.
3. الخلل في قاعدة التعارض الدلالي بين الأشكال الصيدلانية (CREAM vs GEL) يرفض منتجاً
   اسمه يحتوي على الكلمتين معاً (كما هو الحال في "CREAM GEL" — وهو شكل صيدلاني حقيقي).

يُفصَّل كل سبب في `03_ROOT_CAUSE.md`.
