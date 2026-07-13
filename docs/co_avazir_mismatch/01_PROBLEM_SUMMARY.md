# 1 — ملخص المشكلة والأعراض

## وصف المشكلة

| الحقل | القيمة |
|------|--------|
| item_code | `80838` |
| item_name (Excel) | `CO_AVAZIR 5GM EYE OINTMENT` |
| الكمية | 1 (وفي بعض runs = 2) |
| الحالة المرصودة | `matched-only` أو `added-to-cart` |
| المنتج المختار خطأ | `AVAZIR 0.3 % EYE OINT. 5 GM` (score ≈ 15.36) |
| المنتج الصحيح | `CO AVAZIR EYE OINT. 5 GM` / `كو افازير مرهم للعين 5 جم` |

تصحيح المستخدم:
```
80838  CO AVAZIR 5GM EYE OINTMENT  →  CO AVAZIR EYE OINT. 5 GM
                                      كو افازير مرهم للعين 5 جم
```

## الأعراض

### 1) Matching غلط (substitution)

البوت يعتبر `AVAZIR 0.3 % EYE OINT. 5 GM` مطابقة مقبولة لـ `CO_AVAZIR`.
السبب الظاهر في الملخص:
`Accepted best candidate because Extra numeric tokens represent safe omission.`

### 2) المنتج الصحيح موجود لكنه مرفوض

في نفس نتائج API يظهر المرشح الصحيح أولاً بدرجة أعلى (16.8) لكن:
```
accepted=False
rejection_reason=Candidate missing orderable storeProductId
```
لأن `storeProductId=None` و`availableQuantity=0`.

### 3) النتيجة النهائية

- عند match-only: `matched-only` مع المنتج الخاطئ.
- عند order: أحياناً `added-to-cart` للمنتج الخاطئ (مثلاً run `20260713_1126`).

## لماذا خطيرة؟

1. **استبدال صنف تجاري مختلف**: `CO AVAZIR` ≠ `AVAZIR` في كتالوج Tawreed (منتجان منفصلان).
2. قد يُضاف للسلة ويُطلب فعلياً.
3. الإصلاح السابق رفض فقط `AVAZIR EYE DROPS` (شكل مختلف)، ولم يمنع `AVAZIR EYE OINT` (نفس الشكل).

## معيار نجاح الإصلاح

1. `CO_AVAZIR` **لا** يقبل `AVAZIR 0.3 % EYE OINT. 5 GM` كـ best_match.
2. `CO_AVAZIR` **يقبل** `CO AVAZIR EYE OINT. 5 GM` عندما يكون orderable.
3. لا regression على حالات matching السابقة (GARAMYCIN, DIPROSONE, LILI, ...).
