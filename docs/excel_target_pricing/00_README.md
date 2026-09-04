# Excel Target — شرح التسعير (Public vs Purchase) وجدول "Offering stores per item"

هذا المجلد يشرح — بالاعتماد على الكود الفعلي في المستودع — ثلاثة أشياء مرتبطة ببعضها:

1. ما هو `excel_targets` (مخزن Excel) في إعدادات المشروع وكيف يدخل الـ pipeline.
2. لماذا السعر الظاهر في الـ Excel Target هو في الغالب **سعر بيع الصيدلية للجمهور**، وليس سعر الشراء من المخزن.
3. ما الذي يعرضه جدول "Offering stores per item" ولماذا يختلف مصدرا البيانات (Tawreed vs Excel target).

> الفهرس:
> - [01_overview.md](./01_overview.md) — نظارة عمة على الميزة وكيف تنتهي داخل الواجهة.
> - [02_excel_target_source.md](./02_excel_target_source.md) — كيف يقرأ الـ loader صفوف الـ Excel وكيف تُحفظ في الـ candidate dict.
> - [03_public_vs_purchase_price.md](./03_public_vs_purchase_price.md) — شرح مفصّل لازاي سعر واحد في الـ Excel بيتعامل معاه الـ engine على إنه salePrice (سعر بيع للجمهور) وليس سعر شراء للصيدلية.
> - [04_offering_stores_per_item.md](./04_offering_stores_per_item.md) — الجدول اللي اسمه "Offering stores per item" وعلاقته بـ `run_item_stores` و `is_winner`.
> - [05_recommendations.md](./05_recommendations.md) — اقتراحاتي لتحسين الميزة بدون كسر الـ pipeline الحالي.