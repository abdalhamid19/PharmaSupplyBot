# 7 — خطة الإصلاح المنفَّذة

## الخطوة 0 — Reproduce + failing tests (TDD)

1. كتابة `tests/test_co_avazir_mismatch.py`
2. كتابة hypothesis/solution tests
3. تشغيلها والتأكد من الفشل قبل الإصلاح

```powershell
$env:PYTHONPATH = "C:\pyreview\PharmaSupplyBot"
.\.venv\Scripts\python.exe -m unittest tests.test_co_avazir_mismatch -v
```

## الخطوة 1 — إصلاح `_brand_match_check`

ملف: `src/core/drug_matching/normalization/normalizer_matching_brand.py`

1. إضافة `_co_prefixed_brand_mismatch`
2. استدعاؤها قبل فحوص fuzzy/containment
3. رفع عتبة containment لـ `len_diff == 2` من 82 إلى 86

## الخطوة 2 — التحقق من حالة 80838

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_co_avazir_mismatch tests.solutions -v
```

معايير النجاح:
- wrong alone → no best_match
- correct orderable → accepted
- both orderable → correct wins
- production shape (correct unorderable) → wrong not chosen

## الخطوة 3 — Regression suite

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_latest_no_results_regressions tests.core.drug_matching.test_drug_matching_normalizer -v
.\.venv\Scripts\python.exe tools/run_unit_tests.py
```

## الخطوة 4 — توثيق

مجلد `docs/co_avazir_mismatch/` (هذا التقرير).

## ما لم يُغيَّر عمداً (surgical)

- لا تغيير في API/search
- لا تغيير في safe omission العام (ما زال مفيداً لتركيزات topical صحيحة)
- لا تفعيل manufacturer_check المعطوب
- لا hardcode لأسماء منتجات

## ملاحظة تشغيلية

حتى بعد الإصلاح، إذا كان `CO AVAZIR EYE OINT. 5 GM` بلا `storeProductId`
فسينتج `no decisive match` / review بدل طلب AVAZIR بالخطأ.
هذا **سلوك آمن**؛ إصلاح بيانات Tawreed/orderability منفصل.
