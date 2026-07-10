# 8 — خطة التحقق والاختبارات بعد الإصلاح

## أوامر مطلوبة بعد أي تعديل

حسب `docs/project_guidelines.md` وREADME، يجب تشغيل:

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -q
.\.venv\Scripts\python tools\rule_audit.py
```

## اختبارات مركزة يجب أن تنجح

### Matching rules

```powershell
.\.venv\Scripts\python -m unittest tests.test_product_matching -q
```

المطلوب:

- test جديد لـ U RICHI ينجح.
- test قديم `test_semantic_conflict_rejects_isis_detox_for_anise` يظل ناجحاً.
- أي tests لـ manufacturer mismatch أو product matching لا تتأثر.

### Manual review runtime

```powershell
.\.venv\Scripts\python -m unittest tests.core.manual_review.test_manual_review_runtime -q
```

المطلوب:

- `manual_review_queries` يظل يضع `correct_query` في البداية.
- `manual_review_match` يظل لا يفرض match إلا مع `approved=True`.
- `not_matching` يظل يفلتر candidate المحفوظ.

## تحقق يدوي من trace بعد الإصلاح

بعد تشغيل order جديد للصنف، افتح:

```
artifacts/order/wardany/<new_run>/matching_trace_<new_run>.csv
```

وابحث عن:

```
91167
U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM
```

المتوقع:

1. `accepted=True` أو وجود `best_match` للصنف.
2. عدم وجود:
   `Semantic token conflict: CREAM vs GEL, GEL vs CREAM`
   للمرشح الصحيح.
3. score لا يكون منخفضاً بسبب `semantic_penalty=-20`.

## تحقق من order_result_summary

افتح:

```
artifacts/order/wardany/<new_run>/order_result_summary_<new_run>.csv
```

وابحث عن `91167`.

المتوقع:

- `status` ليس `not-orderable` بسبب no match.
- اسم المنتج المطابق هو `U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM` أو اسم Tawreed الرسمي القريب.

## تحقق من Manual Review candidates

لو الصنف لا يزال يحتاج manual review لأي سبب، افتح:

```
artifacts/order/wardany/<new_run>/manual_review_candidates_<new_run>.jsonl
```

المتوقع:

- المنتج الصحيح يظهر ضمن الخيارات، ويفضل في المراكز الأولى.
- `FACIAL WASH` لا يكون أعلى من المنتج الصحيح إذا لم يعد المنتج الصحيح معاقباً بعقوبة semantic خاطئة.

## ملاحظات مهمة عن artifacts القديمة

ملفات مثل:

```
artifacts/order/wardany/20260629_1429/manual_review_candidates_20260629_1429.jsonl
```

لن تتغير تلقائياً بعد إصلاح الكود، لأنها snapshots قديمة. لذلك عند التحقق من الواجهة يجب استخدام run جديد أو حذف/تجاهل artifacts القديمة.

## لماذا لا نحتاج متصفح/تصوير في هذه المرحلة؟

المشكلة الحالية مثبتة من artifacts وunit-level deterministic matching. استخدام المتصفح مفيد فقط للتحقق النهائي إذا أردنا التأكد من API/live search، لكنه ليس ضرورياً لتحديد السبب.

لو تم تشغيل `--debug-browser` لاحقاً، استخدمه للتأكد من أن Tawreed يرجع product orderable وأن البوت يضيفه للسلة، وليس لتشخيص rule نفسها.
