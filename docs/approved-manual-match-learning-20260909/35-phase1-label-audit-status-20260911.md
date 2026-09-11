# Phase 1 — audit labels وintervals

## ما تم

- أضيف Wilson 95% interval إلى precision وrecall في تقرير coverage.
- interval مستقل عن score وranking؛ يعتمد فقط على عدد النجاحات وعدد الحالات المعلّمة.
- `U` و`E_stale` لا يدخلان في denominator الخاص بـprecision.
- عند غياب labels، يبقى التقرير `labels_not_provided` ولا يخترع interval.

## audit template

أضيف الملف:

```text
tests/core/excel_target/fixtures/reviewed_labels_audit.csv
```

ويحتوي 23 مرشحًا من focus audit set على run `20260911_1609` للهدف `البركة شركات`. كل الصفوف حاليًا `label=U` مع ملاحظة `Awaiting independent human adjudication`.

هذا مقصود: لم يتم تحويل score أو compatibility أو ranking إلى حكم بشري. لذلك لا ينتج الملف precision إيجابيًا قبل أن يراجع شخصان مستقلان الصفوف ويملآ `P` أو `N_variant` أو `N_prefix` أو يثبتا `U/E_stale` مع ملاحظات adjudication.

## التحقق

اختبارات coverage الحالية تثبت أن:

- interval يظهر عند وجود labels `P/N`.
- interval محصور في `[0,100]`.
- `U` لا يُحسب كـnegative.
- غياب labels يبقى حالة غير محسوبة.

الـaudit template ليس gold set نهائيًا بعد؛ الحالة الحالية `CONDITIONAL` إلى أن تتم المراجعة البشرية.
