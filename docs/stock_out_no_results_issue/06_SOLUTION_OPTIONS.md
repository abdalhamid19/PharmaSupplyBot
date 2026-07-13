# 06 — الحلول الممكنة مع التقييم

## جدول الحلول

| ID | الحل | Score | أمان | أثر جانبي | حكم |
|----|------|-------|------|-----------|------|
| **S1** | إعادة تصنيف soft-numeric + missing spid (score≥9) → missing storeProductId | **0.96** | عالي | منخفض | **الأفضل / مُطبَّق** |
| **S2** | توسيع `_diagnostic_missing_orderable_identity` فقط (status layer) | 0.78 | عالي | artifacts تبقى برسائل numeric | طبقة أمان إضافية / مُطبَّق جزئياً |
| **S3** | السماح لـ approved name match بدون spid ثم skip not-orderable | 0.88 | عالي | يحتاج skip path واضح | مُطبَّق كمكمّل |
| S4 | اعتبار أي extra pack/strength لـ AMP safe omission دائماً | 0.35 | **منخفض** | قد يطابق تركيزاً خاطئاً عند وجود spid | مرفوض كحل وحيد |
| S5 | خفض medium_score_threshold من 12 إلى 9 عالمياً | 0.40 | متوسط | يؤثر على مسارات أخرى | مرفوض |
| S6 | إجبار AI manual review فقط | 0.25 | — | لا يحل التصنيف | مرفوض |
| S7 | تعديل بيانات الإكسل لإضافة التركيز يدوياً | 0.30 | — | عبء تشغيلي، لا يصلح الجذر | حل مؤقت فقط |

---

## S1 — التفاصيل (المرجّح)

**الملف:** `product_matching_acceptance.py` → `_unorderable_acceptance`

المنطق:

```text
if no storeProductId:
  if numeric acceptance passed:
      → "Candidate missing orderable storeProductId"
  elif rejection is unrequested numeric AND score >= 9:
      → "Candidate missing orderable storeProductId"
  else:
      → keep original rejection
```

### لماذا آمن؟

| حالة | spid | score | النتيجة |
|------|------|-------|---------|
| HAEMOJET الصحيح OOS | فارغ | 10.08 | not-orderable ✅ |
| HALOPERIDOL RETARD OOS | فارغ | 9.90 | not-orderable ✅ |
| HAEMOJET مع spid (قابل للطلب) | موجود | 10.08 | يبقى blocked numeric (لا auto-order) ✅ |
| شقيق أضعف HALOPERIDOL 5 AMP | فارغ | ~6.5 | لا يُعاد تصنيفه ✅ |
| LIMITLESS exact | فارغ | 20.5 | not-orderable كما كان ✅ |

### اختبار الحل

`tests/solutions/test_s1_reclassify_soft_numeric_oos.py` — SOLUTION_SCORE=0.96

---

## S2 — status only

يوسّع `_diagnostic_missing_orderable_identity` ليقبل:

```text
unrequested numeric + score >= 9 + no spid → True
```

مفيد كحزام أمان إن بقي reason رقمياً في مسار قديم.  
وحده لا ينظف سبب الرفض في artifacts.

اختبار: `tests/solutions/test_s2_status_only_soft_numeric.py` — 0.78

---

## S3 — manual review OOS name match

- إزالة شرط spid في name match.
- إذا match بلا spid → `skip_item_exception(... not orderable missing storeProductId ...)`.
- `SummaryStatus.skip_status` يفهم `not orderable` / `missing storeproductid`.

اختبار: `tests/solutions/test_s3_manual_review_oos_name_match.py` — 0.88

---

## لماذا لا S4؟

جعل كل أرقام الحقن “safe” يعني:

```text
HAEMOJET AMP + storeProductId → قد يُطلب 100mg تلقائياً
```

هذا ينقض regression صريح:

`test_phase1_injection_missing_strength_still_requires_review`

---

## التوصية النهائية

**طبّق S1 + S2 + S3 معاً** (طبقات متكاملة):

1. S1 يصحح سبب الرفض ومسار diagnostics.
2. S2 يضمن status حتى لو بقي reason soft.
3. S3 يجعل `approved_match` فعّالاً للأصناف غير القابلة للطلب.

لا تغيّر قواعد قوة التركيز عند وجود `storeProductId`.
