# 8 — التحقق بعد الإصلاح

## أوامر التحقق

من جذر المشروع:

```powershell
$env:PYTHONPATH = "C:\pyreview\PharmaSupplyBot"

# 1) حالة المشكلة
.\.venv\Scripts\python.exe -m unittest tests.test_co_avazir_mismatch -v

# 2) فرضيات + حلول
.\.venv\Scripts\python.exe -m unittest discover -s tests/hypotheses -v
.\.venv\Scripts\python.exe -m unittest discover -s tests/solutions -v

# 3) regressions matching
.\.venv\Scripts\python.exe -m unittest tests.test_latest_no_results_regressions tests.core.drug_matching.test_drug_matching_normalizer -v

# 4) كل unit tests
.\.venv\Scripts\python.exe tools/run_unit_tests.py
```

## نتائج التشغيل (2026-07-13)

| suite | result |
|-------|--------|
| `tests.test_co_avazir_mismatch` | **5/5 OK** (كانت 2/5 قبل الإصلاح) |
| `tests/hypotheses` | **OK** بعد ضبط H4 |
| `tests/solutions` | **7/7 OK** |
| `test_latest_no_results_regressions` + normalizer | **35/35 OK** |
| `tools/run_unit_tests.py` | **470 tests OK** (skipped=20) |

## التحقق المنطقي بعد الإصلاح

```text
CO_AVAZIR vs AVAZIR ointment  → different_brand → rejected
CO_AVAZIR vs CO AVAZIR ointment (orderable) → accepted
CO_AVAZIR vs AVAZIR drops → still rejected
AMIKACIN vs AMIKACIN AMOUN → still accepted (control)
```

## بوابة قبول للمستخدم

بعد أي تشغيل order/match-only جديد لـ item 80838:

1. يجب **ألا** يظهر `AVAZIR 0.3 % EYE OINT. 5 GM` كـ matched product.
2. إن وُجد `storeProductId` لـ `CO AVAZIR EYE OINT. 5 GM` → يُقبل.
3. إن لم يوجد → no-match/review **بدون** استبدال بـ AVAZIR.

## الملفات المتغيرة

| path | change |
|------|--------|
| `src/core/drug_matching/normalization/normalizer_matching_brand.py` | fix |
| `tests/test_co_avazir_mismatch.py` | reproduction tests |
| `tests/hypotheses/*` | hypothesis scoring tests |
| `tests/solutions/*` | solution scoring tests |
| `docs/co_avazir_mismatch/*` | this report |
