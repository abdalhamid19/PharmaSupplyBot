# 03 — الأسباب المحتملة مع الترجيح (Scoring)

## جدول الأسباب

| ID | الفرضية | Score | دورها في العَرَض | حكم |
|----|---------|-------|------------------|------|
| H1 | رفض `unrequested numeric tokens` يمنع قبول المرشح الصحيح | **0.95** | السبب المباشر لعدم `best_match` | مساهم أساسي في طبقة القبول |
| H2 | مصنّف الحالة يشترط score≥12 أو reason=missing-id | **0.98** | السبب المباشر لكتابة `no-results` | **السبب الأساسي للعَرَض الظاهر** |
| H3 | `approved_match` name match يتطلب `storeProductId` | **0.90** | لماذا التصحيح اليدوي “موجود ولا يُطبَّق” | مساهم قوي ثانوي |
| H4 | رسالة الرفض كانت hardcoded = `storeProductId` | **0.55** | تشويش التشخيص في artifacts | عيب عرض/تشخيص فقط |
| H5 | ترتيب acceptance يخفي missing-id خلف numeric | **0.92** | لماذا لا يظهر reason الكلاسيكي not-orderable | مساهم هيكلي مرتبط بـ H1+H2 |
| H6 | المنتج غير موجود فعلاً في Tawreed | **0.05** | — | **مرفوض** (matching_trace + CSV) |
| H7 | Manual review DB فارغة / lookup فاشل | **0.20** | artifacts تُظهر `saved_manual_review_decision=approved_match` | **مرفوض كسبب رئيسي** |
| H8 | AI order flow يفسد القرار | **0.15** | ai_enabled=False في الصفوف المفحوصة | مرفوض |

---

## السبب الأساسي المرجّح (Root Cause Chain)

المشكلة **ليست** أن البحث لا يجد الصنف.  
المشكلة **سلسلة من ثلاث حلقات**:

### الحلقة 1 — قبول المطابقة (H1 + H5) — Score 0.95

الاستعلام قصير بدون تركيز كامل:

- `HALOPERIDOL RETARD 1AMP` → extra `{50}`
- `HAEMOJET AMP` → extra `{100, 2, 6}`

`components_match` يقول **متوافق**، لكن safe-omission للحقن/السوائل **يفشل** لأن الاستعلام بلا `dosage_nums`.

النتيجة: رفض soft باسم مضلل سابقاً:

```text
unrequested numeric token: storeProductId   # كان hardcoded!
```

### الحلقة 2 — تصنيف الحالة (H2) — Score 0.98 ← **الأساسي للعرض**

`_diagnostic_missing_orderable_identity`:

1. إذا reason = missing storeProductId → not-orderable ✅
2. وإلا إذا score ≥ 12 وبدون hard rejection → not-orderable ✅
3. وإلا → لا شيء → **no-results**

للأصناف المشكلة: reason ≠ missing-id **و** score < 12 → **no-results**.

### الحلقة 3 — Manual review (H3) — Score 0.90

حتى مع `approved_match`، مطابقة الاسم كانت تتخطى المرشح بلا spid → لا فرض تطابق → لا مسار “تعرفنا عليه لكنه غير قابل للطلب”.

---

## لماذا السبب الأساسي هو H2 وليس H1 وحده؟

- H1 **مقصود جزئياً**: لا نريد auto-order لـ `HAEMOJET AMP` → `HAEMOJET 100 MG...` عند وجود `storeProductId` بدون تأكيد تركيز.
- العيب الذي يشتكي منه المستخدم هو **العرض/التصنيف**: يظن النظام أن الصنف “غير موجود”.
- أصناف مشابهة (LIMITLESS) تمر H1 بنجاح فتصل لـ missing-id ثم not-orderable.
- إذن الخلل الوظيفي المطلوب إصلاحه أولاً: **عند التعرف على صف كتالوج بلا spid بدرجة عالية، صِفه not-orderable**.

H1/H5 يفسران *لماذا لم يُكتب missing-id*.  
H2 يفسر *لماذا ظهر no-results*.  
H3 يفسر *لماذا approved_match لم ينقذ الموقف*.

---

## نموذج سببي مبسّط

```text
Query ناقص تركيز
   ↓
extra numeric tokens
   ↓
reject soft (no best_match)     ← H1
   ↓
reason != missing-id
score < 12                      ← H2
   ↓
status = no-results   ← العَرَض
   +
approved_match skips no-spid    ← H3
```

---

## ما ليس السبب

1. **غياب الصنف من Tawreed** — matching_trace يُظهر المرشح الصحيح.
2. **فشل حفظ manual review** — summary يحتوي `saved_manual_review_decision=approved_match`.
3. **مشكلة شبكة/API عامة** — أصناف أخرى في نفس التشغيل تصبح `not-orderable` بنجاح.
