# 08 — التحقق بعد الإصلاح

## 1) التغييرات المطبّقة

| ملف | التغيير |
|-----|---------|
| `src/core/matching/product_matching_acceptance.py` | `_unorderable_acceptance` + رسالة numeric حقيقية |
| `src/tawreed/tawreed_summary.py` | soft-numeric not-orderable + skip phrases |
| `src/core/manual_review/manual_review_helpers.py` | name match بدون اشتراط spid |
| `src/tawreed/matching/tawreed_search_logic.py` | skip not-orderable عند MR match بلا spid |

## 2) ملفات الاختبار الجديدة

| ملف | الدور |
|-----|-------|
| `tests/test_haloperidol_haemojet_no_results.py` | بوابة المشكلة |
| `tests/hypotheses/test_h1_*.py` … `test_h5_*.py` | إثبات الفرضيات |
| `tests/solutions/test_s1_*.py` … `test_s3_*.py` | تقييم الحلول |

## 3) أوامر التحقق

### بوابة المشكلة (يجب أن تنجح دائماً)

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_haloperidol_haemojet_no_results -v
```

### الفرضيات + الحلول

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/hypotheses -p "test_h*_*.py" -v
.\.venv\Scripts\python.exe -m unittest `
  tests.solutions.test_s1_reclassify_soft_numeric_oos `
  tests.solutions.test_s2_status_only_soft_numeric `
  tests.solutions.test_s3_manual_review_oos_name_match -v
```

### regressions السابقة

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_latest_no_results_regressions -v
```

### مجموعة أوسع

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

## 4) نتائج متوقعة بعد الإصلاح (unit)

| سيناريو | best_match | reason/status |
|---------|------------|---------------|
| HALOPERIDOL OOS | None | missing storeProductId → **not-orderable** |
| HAEMOJET OOS | None | missing storeProductId → **not-orderable** |
| HAEMOJET + spid بدون تركيز | None | unrequested numeric (آمن) |
| LIMITLESS OOS | None | missing storeProductId → **not-orderable** |
| approved_match بلا spid | skip | **not-orderable** |

## 5) معيار “المشكلة اتحلت”

- [x] اختبارات `test_haloperidol_haemojet_no_results` خضراء
- [x] regressions `test_latest_no_results_regressions` خضراء
- [x] فرضيات H1–H5 خضراء
- [x] حلول S1–S3 خضراء
- [x] suite كامل: `478 tests OK (skipped=20)` بتاريخ 2026-07-13
- [ ] تشغيل order حي يؤكد status في summary (عند توفر الجلسة)

## 6) كيف تستخدم الاختبارات عند تجربة حل بديل

1. نفّذ الحل البديل.
2. شغّل:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_haloperidol_haemojet_no_results -v
```

3. إذا فشل أي اختبار → الحل غير كافٍ أو كسر ضمانة أمان.
4. إذا نجح بالكامل → السيناريو المبلَّغ عنه محلول على مستوى المنطق.
