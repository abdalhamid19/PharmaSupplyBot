# 01 — وصف المشكلة بالتفصيل

## 1) ما يراه المستخدم

| item_code | item_name | status الفعلي | reason |
|-----------|-----------|---------------|--------|
| 29244 | HALOPERIDOL RETARD 1AMP | `no-results` | No decisive match found ... after 8 queries |
| 74603 | HAEMOJET AMP | `no-results` | No decisive match found ... after 4 queries |

المعنى الظاهر للمستخدم: **الصنف غير موجود / لا يوجد تطابق**.

## 2) ما هو موجود فعلياً في الكتالوج

من `data/input/tawreed_products.csv`:

```text
هالوبيريدول ريتارد 50 مجم / مل امبول,HALOPERIDOL RETARD 50 MG / ML I.M.AMP.,,7092.0,0.0
هيموجيت 100 مجم / 2 مل 6 امبول,HAEMOJET 100 MG / 2 ML 6 AMPS.,2437676.0,7024.0,130.0
```

ملاحظات:

- **HALOPERIDOL RETARD**: `storeProductId` فارغ دائماً، الكمية `0.0` → غير قابل للطلب.
- **HAEMOJET AMP**: يوجد في الكتالوج؛ في تشغيلات البحث الحية يظهر أحياناً **بدون** `storeProductId` عندما لا يكون قابلاً للطلب من المستودع الحالي.

## 3) ما هو موجود في التصحيح اليدوي

| item | manual_decision | correct EN | correct AR |
|------|-----------------|------------|------------|
| 29244 HALOPERIDOL RETARD 1AMP | `approved_match` | HALOPERIDOL RETARD 50 MG / ML I.M.AMP. | هالوبيريدول ريتارد 50 مجم / مل امبول |
| 74603 HAEMOJET AMP | `approved_match` | HAEMOJET 100 MG / 2 ML 6 AMPS. | هيموجيت 100 مجم / 2 مل 6 امبول |

الغرابة: التصحيح اليدوي **موافق** على الصنف الصحيح، لكن التشغيل يكتب `no-results` وكأن شيئاً لم يُحفظ.

## 4) السلوك المتوقع

مثل باقي الأصناف النافدة الناجحة (أمثلة حقيقية من `20260713_1257`):

| item | status | rejection |
|------|--------|-----------|
| LIMITLESS LIPOFERREX 40 MG 30 TABS | **`not-orderable`** | Candidate missing orderable storeProductId |
| GLIPTUS PLUS 50/500MG 30 TABS. | **`not-orderable`** | Candidate missing orderable storeProductId |

المتوقع للأصناف المشكلة:

1. النظام **يتعرّف** على الصنف الصحيح.
2. **لا** يضيفه للسلة.
3. يكتب status = **`not-orderable`** (أو `matched-but-unavailable`) مع اسم المنتج المطابق.
4. **لا** يكتب `no-results`.

## 5) السلوك الفعلي قبل الإصلاح

1. البحث يجد المرشح الصحيح (matching_trace موجود).
2. القبول يرفضه بسبب أرقام تركيز/عبوة زائدة في الاسم.
3. الدرجة ~9.9–10.1 < 12.
4. سبب الرفض ليس `Candidate missing orderable storeProductId`.
5. مصنّف الحالة لا يعتبره `not-orderable`.
6. النتيجة النهائية: **`no-results`**.
7. `approved_match` لا يفرض التطابق لأن المرشح بلا `storeProductId`.

## 6) الفرق الجوهري عن LIMITLESS/GLIPTUS

| البعد | LIMITLESS / GLIPTUS | HALOPERIDOL / HAEMOJET |
|-------|---------------------|-------------------------|
| الاستعلام يحتوي أرقام التركيز | نعم (40, 30 / 50, 500) | لا / جزئي فقط (`1AMP`) |
| extra numeric tokens | لا | نعم (`50` / `100,2,6`) |
| rejection reason | missing storeProductId | unrequested numeric token |
| score | ~20.5 ≥ 12 | ~9.9–10.1 < 12 |
| status | not-orderable ✅ | no-results ❌ |
| approved_match | موجود | موجود لكن بلا أثر |

## 7) معيار نجاح الإصلاح (قابل للتحقق)

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_haloperidol_haemojet_no_results -v
```

يجب أن ينجح بالكامل. أي فشل يعني أن المشكلة لم تُحل.
