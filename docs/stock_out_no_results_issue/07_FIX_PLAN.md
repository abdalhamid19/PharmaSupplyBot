# 07 — خطة الحل المرتبة

## الهدف القابل للتحقق

بعد التنفيذ، لأي من:

- `29244 HALOPERIDOL RETARD 1AMP` + مرشح `HALOPERIDOL RETARD 50 MG / ML I.M.AMP.` بلا spid  
- `74603 HAEMOJET AMP` + مرشح `HAEMOJET 100 MG / 2 ML 6 AMPS.` بلا spid  

يجب:

1. `best_match is None` (لا طلب تلقائي).
2. `final_reason == "Candidate missing orderable storeProductId"` (أو skip not-orderable عبر MR).
3. `SummaryStatus` → **`not-orderable`**.
4. عند وجود `storeProductId` وبدون تركيز في الاستعلام → **لا auto-match** (يبقى numeric block).

بوابة التحقق:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_haloperidol_haemojet_no_results -v
```

---

## الخطوات (بالترتيب)

### Step 0 — اختبار أحمر/أخضر للمشكلة

- إنشاء `tests/test_haloperidol_haemojet_no_results.py`.
- تشغيله قبل الإصلاح → كان سيفشل على not-orderable classification.
- **تم.**

### Step 1 — S1: `_unorderable_acceptance`

**ملف:** `src/core/matching/product_matching_acceptance.py`

- عند غياب spid:
  - قبول numeric → missing storeProductId.
  - soft numeric + score≥9 → missing storeProductId.
- إصلاح رسالة `_numeric_acceptance` لتذكر الـ tokens الحقيقية.

**تحقق:** `tests/solutions/test_s1_reclassify_soft_numeric_oos.py`  
**تم.**

### Step 2 — S2: توسيع status classifier

**ملف:** `src/tawreed/tawreed_summary.py`

- soft numeric + score≥9 + no spid → not-orderable.
- hard rejections (identity/brand/semantic) تبقى مستبعدة.
- `skip_status` يفهم `not orderable` و `missing storeproductid`.

**تحقق:** `tests/solutions/test_s2_status_only_soft_numeric.py`  
**تم.**

### Step 3 — S3: manual review بدون spid

**ملفات:**

- `src/core/manual_review/manual_review_helpers.py`
- `src/tawreed/matching/tawreed_search_logic.py`

- name match لا يتجاهل المرشح بلا spid.
- `manual_review_result` يرفع skip not-orderable عند غياب spid.

**تحقق:** `tests/solutions/test_s3_manual_review_oos_name_match.py`  
**تم.**

### Step 4 — Regression suite

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_haloperidol_haemojet_no_results `
  tests.test_latest_no_results_regressions `
  tests.hypotheses.test_h1_unrequested_numeric_blocks_oos `
  tests.hypotheses.test_h2_status_threshold_blocks_not_orderable `
  tests.hypotheses.test_h3_manual_review_name_requires_spid `
  tests.hypotheses.test_h4_hardcoded_numeric_message `
  tests.hypotheses.test_h5_acceptance_order_hides_missing_id `
  tests.solutions.test_s1_reclassify_soft_numeric_oos `
  tests.solutions.test_s2_status_only_soft_numeric `
  tests.solutions.test_s3_manual_review_oos_name_match -v
```

### Step 5 — تشغيل اختبارات أوسع

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

### Step 6 — تحقق تشغيلي (عند توفر الجلسة)

إعادة تشغيل match-only / order run صغير للأصناف:

- 29244, 74603

المتوقع في summary:

```text
status=not-orderable
matched/blocked name = الاسم الصحيح
```

---

## ما لا يُفعل

1. لا توسيع safe-omission للحقن بلا تركيز عند وجود spid.
2. لا خفض `medium_score_threshold` عالمياً.
3. لا refactor كبير خارج الملفات المذكورة.
4. لا تغيير سلوك LIMITLESS/GLIPTUS الناجح أصلاً.

---

## خطة الرجوع (Rollback)

إن ظهرت false not-orderable واسعة:

1. ارفع عتبة score من 9.0 إلى 10.0 أو 10.5.
2. أو عطّل إعادة التصنيف في `_unorderable_acceptance` وأبقِ S2 فقط.
3. أعد تشغيل `tests.test_haloperidol_haemojet_no_results` بعد كل تغيير.
