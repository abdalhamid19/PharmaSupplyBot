# 01 — نظارة عمة على الميزة

## ايه هو الـ Excel Target في الكود؟

في `config.yaml` عندك قسم اسمه `excel_targets`. كل entry فيه عبارة عن pricelist لـ "مخزن" بصيغة ملف Excel. الـ engine بتاع الـ matching ما بيفرش الـ Excel مباشرة، لأ — هو بيحوّله لـ list من `TargetProduct`s عن طريق:

- `src/core/excel_target/excel_target_loader.py` → `load_target_catalog_from_excel(...)`
- بعدين `iter_target_candidates(...)` بتحوّل كل صف لـ candidate dict بنفس الـ shape اللي بيستهلكه الـ core matcher (نفس الـ keys اللي بيستخدمها Tawreed: `productNameEn`, `salePrice`, `discountPercent`, ...).

بعد ما تتحوّل، الـ rows دي بتدخل في الـ matching engine بالـ `source="excel_target"` وبتتنافس على لقب "الفائز" (winner) جنب الـ candidates اللي جاية من Tawreed API.

## الـ pipeline المختصر

```
Excel file
  └─► load_target_catalog_from_excel()            # excel_target_loader.py
        └─► TargetProduct(name, code, price, discount)
              └─► iter_target_candidates()        # بيولّد dict بـ salePrice
                    └─► core matcher
                          ├─ winner per item
                          └─ all offering stores  → run_item_stores (SQLite)
                                └─► UI: "Offering stores per item"
```

الـ winner بيتحسب في `src/cli/commands/cli_order.py` على أساس **أقل `purchase_price`** (مع خصم مطبق)، والـ is_winner بيتسجل في `run_item_stores`.

## ليش ده مهم؟

لأن الـ "best deal" اللي بيحسبه الـ system للصيدلي لازم يكون سعر **الشراء** من المخزن (هو اللي بيدفعه فعلاً)، مش سعر بيعه للجمهور. ولو الـ Excel بيحمل سعر الجمهور (الـ retail price) بدل سعر الشراء، الـ winner هيكون غلط منطقياً.