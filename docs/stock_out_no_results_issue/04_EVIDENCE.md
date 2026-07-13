# 04 — الأدلة من Artifacts والتشغيل الحي

## 1) matching_trace — HALOPERIDOL (run 20260713_1126 / 20260712_1107)

```text
item_code=29244
item_name=HALOPERIDOL RETARD 1AMP
candidate=HALOPERIDOL RETARD 50 MG / ML I.M.AMP.
store_product_id= (empty)
score≈9.898305
accepted=False
rejection_reason=unrequested numeric token: storeProductId
```

مرشح ثانوي أضعف:

```text
HALOPERIDOL 5 MG / ML I.M. / I.V. 5 AMP.  score≈8.98  (أو ~6.5 في العزل)
```

## 2) matching_trace — HAEMOJET (run 20260713_1257)

```text
item_code=74603
item_name=HAEMOJET AMP
candidate=HAEMOJET 100 MG / 2 ML 6 AMPS.
store_product_id= (empty)
score≈10.076923
accepted=False
rejection_reason=unrequested numeric token: storeProductId
```

مرشحون آخرون (أضعف / شكل مختلف):

- HAEMOJET 50 MG / 5 ML SYRUP 100 ML — spid موجود أحياناً، score أقل
- HAEMOJET 100 MG 36 S.G.CAPS. — score أقل

## 3) order_item_summary — status النهائي

من `artifacts/order/wardany/20260713_1257/order_item_summary_*.csv`:

```text
74603,HAEMOJET AMP,...,no-results,No decisive match found...
saved_manual_review_decision=approved_match
higher_scoring_rejection_reason=unrequested numeric token: storeProductId
```

مقارنة مع صنف يعمل correctly:

```text
86815,LIMITLESS LIPOFERREX 40 MG 30 TABS,...,not-orderable,...
rejection=Candidate missing orderable storeProductId
score≈20.5
saved_manual_review_decision=approved_match
```

## 4) إعادة إنتاج حية (unit-level) قبل الإصلاح

```text
HALOPERIDOL RETARD 1AMP -> ...50 MG... spid=
  best=False  score=9.90  rej=unrequested numeric...  not_orderable_diag=False

HAEMOJET AMP -> ...100 MG / 2 ML 6 AMPS. spid=
  best=False  score=10.08 rej=unrequested numeric...  not_orderable_diag=False

LIMITLESS ...40 MG 30 TABS -> same name spid=
  best=False  score=20.5  rej=Candidate missing orderable storeProductId  not_orderable_diag=True
```

manual review name match:

```text
HALOPERIDOL name match without spid → forced=False   # قبل الإصلاح
HAEMOJET name match with spid=2099814 → forced=True
```

## 5) extra numeric tokens (دليل كمي)

| Query | Candidate | extra |
|-------|-----------|-------|
| HALOPERIDOL RETARD 1AMP | HALOPERIDOL RETARD 50 MG / ML I.M.AMP. | `{50}` |
| HAEMOJET AMP | HAEMOJET 100 MG / 2 ML 6 AMPS. | `{100,2,6}` |
| LIMITLESS LIPOFERREX 40 MG 30 TABS | same | `{}` |

## 6) components_match

لكل من حالتي المشكلة: `components_match = True` (البراند/الشكل متوافقان).  
إذن الرفض **ليس** hard identity/brand conflict؛ هو soft numeric + missing orderable id.

## 7) safe omission

```text
HALOPERIDOL: _any_safe_omission({50}) = False
HAEMOJET:    _any_safe_omission({100,2,6}) = False
```

لأن الاستعلام بلا dosage strength يشارك المرشح.

## 8) عتبة score

| مرشح | score | ≥12؟ | ≥9؟ |
|------|-------|------|-----|
| HALOPERIDOL RETARD الصحيح | 9.90 | لا | نعم |
| HAEMOJET AMP الصحيح | 10.08 | لا | نعم |
| HALOPERIDOL 5 AMP الشقيق | ~6.5 | لا | لا |
| HAEMOJET CAPS | ~6.3 | لا | لا |
| HAEMOJET SYRUP | ~6.0 | لا | لا |

هذا يبرر عتبة 9.0 بعد الإصلاح: تلتقط الصحيح وتترك الأشقاء الضعفاء.
