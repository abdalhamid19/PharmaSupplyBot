# 2 — خريطة الكود المتورط

## تدفق المطابقة (production path)

```
Excel Item(80838, CO_AVAZIR 5GM EYE OINTMENT)
  → search_queries_for_item()          # product_matching_queries.py
  → Tawreed API search results
  → explain_best_product_match()       # product_matching.py
      → _build_candidate_diagnostics() # product_matching_decisions.py
          → score breakdown            # product_matching_scoring.py
          → _diagnostic_acceptance()   # product_matching_acceptance.py
              → _check_rejections()
                  → _candidate_variant_rejection
                  → compatibility_rejection_reason  # matching_penalties.py
                  → _candidate_component_rejection
                      → parse_drug() + components_match()
                          → _brand_match_check()    # ★ السبب الأساسي
                          → form/dosage checks
              → _numeric_acceptance / safe omission
              → orderable storeProductId gate
      → _decision_from_diagnostics()   # يختار أعلى accepted
```

## الملفات الحرجة

| ملف | الدور |
|-----|------|
| `src/core/drug_matching/normalization/normalizer_matching_brand.py` | فحص العلامة — **موقع الإصلاح** |
| `src/core/drug_matching/normalization/normalizer_matching_core.py` | orchestrator لـ components_match |
| `src/core/matching/product_matching_acceptance.py` | قبول/رفض + safe omission + storeProductId |
| `src/core/matching/product_matching_scoring.py` | overlap/sequence scoring |
| `src/core/matching/matching_penalties.py` | distinguishing/extra brand tokens |
| `src/core/matching/product_matching_queries.py` | توليد استعلامات البحث |
| `data/input/tawreed_products.csv` | كتالوج المنتجات |

## نقاط القرار التي فشلت لهذه الحالة

### A) `_brand_match_check` (قبل الإصلاح)

- `parse_drug("CO_AVAZIR ...")` → brand = `COAVAZIR`
- `parse_drug("AVAZIR 0.3 % EYE OINT. 5 GM")` → brand = `AVAZIR`
- `AVAZIR in COAVAZIR` = True (containment)
- `len_diff = 2`, `fuzz.ratio ≈ 85.71`
- الشرط القديم: يرفض containment فقط إذا `len_diff==2` **و** `ratio < 82`
- 85.71 ≥ 82 ⟹ **يقبل العلامة**

### B) form/dosage

- form الطرفين = `OINT` ⟹ لا `different_form`
- `0.3%` إضافي يمر عبر `_safe_omitted_percentage_concentration` (topical/eye)

### C) orderability

- الصحيح: score 16.8 لكن `storeProductId` فارغ ⟹ مرفوض
- الخطأ: score 15.36 + orderable ⟹ **يفوز**

## ما لم يكن السبب

| مسار | لماذا ليس السبب؟ |
|------|------------------|
| توليد الاستعلامات | الاستعلامات تحتوي `CO AVAZIR` والمنتج الصحيح يظهر في النتائج |
| CONFLICT form OINT vs DROPS | drops مرفوضة مسبقاً؛ المشكلة ointment vs ointment |
| البحث API | API يرجع المرشحين الصحيح والخاطئ معاً |
