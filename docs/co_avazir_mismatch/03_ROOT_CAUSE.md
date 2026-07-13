# 3 — الأسباب المحتملة + scoring + السبب الأساسي

## منهجية الـ scoring

لكل فرضية:
- **Evidence (0–40)**: أدلة artifacts/كود/تشغيل
- **Necessity (0–30)**: هل بدونها يحدث الخطأ؟
- **Sufficiency (0–30)**: هل وحدها تفسر النتيجة النهائية؟
- **Total /100**

## جدول الفرضيات

| ID | الفرضية | Evidence | Necessity | Sufficiency | **Total** | الحكم |
|----|---------|----------|-----------|-------------|-----------|-------|
| **H1** | brand containment يقبل `COAVAZIR≈AVAZIR` (len_diff=2, ratio~85.7) | 40 | 30 | 25 | **95** | **سبب أساسي** |
| **H2** | المنتج الصحيح بلا `storeProductId` فيُرفض رغم score أعلى | 38 | 25 | 15 | **78** | **سبب مساهم حاسم** |
| **H3** | safe omission لتركيز 0.3% + form OINT يسمح بقبول الخطأ | 30 | 15 | 10 | **55** | مساهم ثانوي (بعد H1) |
| **H4** | المشكلة هي AVAZIR drops (شكل مختلف) | 10 | 0 | 0 | **10** | **منفية** (مرفوضة مسبقاً) |
| **H5** | فشل توليد queries / عدم ظهور المنتج الصحيح | 5 | 0 | 0 | **5** | **منفية** |

## السبب الأساسي المرجّح (H1)

```
_brand_match_check يعتبر COAVAZIR مطابقاً لـ AVAZIR
لأن AVAZIR محتواة داخل COAVAZIR وفرق الطول حرفان والنسبة 85.7 ≥ 82.
```

بدون H1: حتى لو كان AVAZIR orderable، كان يُرفض بـ `different_brand`.

## السبب المساهم (H2)

```
CO AVAZIR EYE OINT. 5 GM يظهر في نتائج البحث بدرجة 16.8
لكن storeProductId=null → rejected.
النظام يختار أول مرشح orderable مقبول → AVAZIR 15.36.
```

H2 لا يخلق القبول الخاطئ؛ يزيل المنافس الصحيح فقط.
**حتى لو توفر storeProductId لاحقاً، يجب أن تبقى H1 محلولة** حتى لا يُقبل AVAZIR عند غياب الصحيح.

## سلسلة الفشل (production)

```
1. Query: CO_AVAZIR 5GM EYE OINTMENT
2. API يرجع:
   [1] CO AVAZIR EYE OINT. 5 GM     score=16.8  ❌ no storeProductId
   [2] AVAZIR 0.3 % EYE OINT. 5 GM  score=15.36 ✅ brand pass + safe omission + orderable
   [3] CO AVAZIR EYE SUSP. DROPS    score=6.81  ❌ form/numeric
   [4] AVAZIR 0.3 % EYE DROPS       score=5.16  ❌ different_form
3. best_match = [2] AVAZIR ointment  ← خطأ
```

## لماذا إصلاح drops السابق لم يكفِ؟

`docs/MATCHING_WRONG_SUBSTITUTIONS_FIX_REPORT.md` أصلح:
`CO_AVAZIR` vs `AVAZIR EYE DROPS` → `different_form`.

لكن الحالة الحية هي **ointment vs ointment**، وليست drops.
