# تحليل مشكلة: أصناف نافدة تُصنَّف `no-results` بدل `not-orderable`

**التاريخ:** 2026-07-13  
**الأصناف:** `29244 HALOPERIDOL RETARD 1AMP` · `74603 HAEMOJET AMP`  
**القواعد:** `docs/project_guidelines.md` + `docs/starting_prompt.md`  
**الحالة:** تم التشخيص + الإصلاح الجراحي + التحقق بالاختبارات

---

## الفهرس

| الملف | المحتوى |
|------|---------|
| [01_PROBLEM_SUMMARY.md](01_PROBLEM_SUMMARY.md) | وصف المشكلة والأعراض والمخرجات المرصودة |
| [02_CODE_MAP.md](02_CODE_MAP.md) | خريطة الكود المتورط بالكامل |
| [03_ROOT_CAUSE.md](03_ROOT_CAUSE.md) | الأسباب المحتملة مع scoring وترجيح السبب الأساسي |
| [04_EVIDENCE.md](04_EVIDENCE.md) | أدلة artifacts والتشغيل الحي |
| [05_HYPOTHESES_TESTS.md](05_HYPOTHESES_TESTS.md) | ملفات اختبار لكل فرضية ونتائجها |
| [06_SOLUTION_OPTIONS.md](06_SOLUTION_OPTIONS.md) | الحلول الممكنة مع scoring |
| [07_FIX_PLAN.md](07_FIX_PLAN.md) | خطة الحل المرتبة ومعايير النجاح |
| [08_VERIFICATION.md](08_VERIFICATION.md) | التحقق بعد الإصلاح وأوامر الاختبار |

---

## الخلاصة في سطرين

المنتج **موجود** في نتائج البحث لكنه **بدون `storeProductId`** (غير قابل للطلب).  
خوارزمية القبول ترفضه أولاً بسبب أرقام تركيز/عبوة غير مذكورة في الاستعلام، فيصبح السبب `unrequested numeric` بدرجة ~10 (أقل من عتبة 12)، فيُكتب **`no-results`** بدل **`not-orderable`**.  
التصحيح اليدوي `approved_match` لا يُطبَّق لأن مطابقة الاسم كانت تتخطى أي مرشح بلا `storeProductId`.

---

## اختبار التحقق السريع (قبل/بعد أي حل)

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_haloperidol_haemojet_no_results -v
```

- إذا **نجح** → المشكلة محلولة لهذا السيناريو.
- إذا **فشل** → ما زال التصنيف أو مسار manual review مكسوراً.
