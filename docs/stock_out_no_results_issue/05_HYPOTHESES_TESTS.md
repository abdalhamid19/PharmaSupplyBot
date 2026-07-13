# 05 — اختبارات الفرضيات (Hypothesis Tests)

كل فرضية لها ملف اختبار مستقل تحت `tests/hypotheses/`.

## أوامر التشغيل

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.hypotheses.test_h1_unrequested_numeric_blocks_oos `
  tests.hypotheses.test_h2_status_threshold_blocks_not_orderable `
  tests.hypotheses.test_h3_manual_review_name_requires_spid `
  tests.hypotheses.test_h4_hardcoded_numeric_message `
  tests.hypotheses.test_h5_acceptance_order_hides_missing_id -v
```

## النتائج والـ Scoring

| Test file | فرضية | Score | نتيجة بعد الإصلاح | ماذا تثبت |
|-----------|-------|-------|-------------------|-----------|
| `test_h1_unrequested_numeric_blocks_oos.py` | H1 | 0.95 | PASS | الاستعلام يولّد extra nums والمرشح يُرفض من القبول |
| `test_h2_status_threshold_blocks_not_orderable.py` | H2 | **0.98** | PASS | score بين 9 و 12؛ بعد الإصلاح status=not-orderable |
| `test_h3_manual_review_name_requires_spid.py` | H3 | 0.90 | PASS | name match يعمل الآن بدون spid ومع spid |
| `test_h4_hardcoded_numeric_message.py` | H4 | 0.55 | PASS | الرسالة تذكر tokens حقيقية لا اسم الحقل |
| `test_h5_acceptance_order_hides_missing_id.py` | H5 | 0.92 | PASS | OOS عالي الدرجة يُبلَّغ كـ missing storeProductId |

## تفسير الـ scoring

- **H2 أعلى score** لأنه يفسر العَرَض النهائي (`no-results` في summary) مباشرة.
- **H1/H5** يفسران طبقة القبول التي تمنع الوصول لسبب missing-id الكلاسيكي.
- **H3** يفسر لغز “التصحيح اليدوي موجود لكن لا أثر”.
- **H4** عيب تشخيصي؛ إصلاحه يحسّن القابلية للقراءة فقط.

## علاقة الفرضيات بالـ regression الرئيسي

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_haloperidol_haemojet_no_results -v
```

هذا الملف هو **بوابة النجاح**: إذا نجح بعد أي تغيير، فالسيناريو الإنتاجي المبلَّغ عنه محلول.
