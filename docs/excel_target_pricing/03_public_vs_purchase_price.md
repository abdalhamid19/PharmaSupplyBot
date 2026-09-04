# 03 — Public vs Purchase price في Excel Target

> **حُسم السياق الفعلي:** الـ Excel Target في الـ workflow بتاع المشروع بيحمل **سعر بيع الصيدلية للجمهور (retail)** وليس سعر شراء الصيدلية من المخزن.
>
> ده غيّر الـ diagnosis: الـ loader **صح في الـ semantic**، المشكلة كلها في (أ) الـ winner logic اللي بيتجاهل الصفوف دي، و(ب) الـ UI اللي مش بتوضّح إن الرقم ده سعر بيع للعميل النهائي.

## الخلاصة في جملة واحدة

**سعر الـ Excel Target بيتسجل صح كـ `salePrice`/`public_price` (سعر بيع للجمهور). الـ pipeline بيتعامل معاه على إنه retail price. لكن الـ winner بيتختار على أساس أقل `purchase_price`، فالـ Excel target rows عمرها ما بتكسب الـ competition — وده يخلّي الـ feature شبه معطّلة.**

## الـ semantic في الـ Tawreed data (reference)

| Field                          | المعنى                                  |
|--------------------------------|-----------------------------------------|
| `retailPrice` / `publicPrice`  | سعر بيع الجمهور النهائي (retail)        |
| `salePrice`                    | سعر الشراء الفعلي للصيدلية بعد الخصم (wholesale/net) |

من `docs/order_runs_sqlite/02_data_model.md:172-173`:

```sql
public_price       REAL,     -- retailPrice — سعر الجمهور
purchase_price     REAL,     -- salePrice   — ما تدفعه أنت فعلاً
```

## الـ semantic في الـ Excel Target loader

الـ loader في `excel_target_loader.py:39-58` بياخد عمود سعر واحد وبيحطه في:

```python
"salePrice": float(self.price or 0.0),
```

ده **صح** لما الـ Excel بيحمل retail price — لأن `salePrice` في الـ Tawreed semantic = retail.

وكمان في `cli_order_excel_target.py:470-482`:

```python
"salePrice":     float(price),
"sellingPrice":  float(price),
"publicPrice":   float(price),    # ← populated
"purchasePrice": None,           # ← left empty
"discountPercent": ...,
```

تعليق في نفس الملف بيقول (`cli_order_excel_target.py:456-461`):

```
catalogs only carry the pharmacy's purchase price + discount + name, so
the public/retail price is left empty and the warehouse identity is
```

> ⚠️ **التعليق ده مغلوط في سياق الـ workflow بتاعنا** — هو بيقول إن الـ Excel يحوي سعر شراء الصيدلية، بس الفعلي إن الـ Excel بيحوي سعر بيع الصيدلية للجمهور. لازم يتحدّث.

## الـ winner logic ولماذا الـ Excel target ما بيكسبش

في `src/cli/commands/cli_order.py:313-328`:

```python
# Cheapest non-null purchase_price wins; ties broken by the higher
# discount_percent.
cand_price = candidate.get("purchase_price")
curr_price = current.get("purchase_price")
if cand_price is None and curr_price is not None:
    return False   # Tawreed wins (لأنه عنده purchase_price)
if cand_price is not None and curr_price is None:
    return True    # ← الـ branch ده مش بيتنفّذ للـ Excel target
```

- الـ Excel target rows عندها `purchase_price = None`.
- الـ Tawreed rows عندها `purchase_price = salePrice` (سعر الشراء بعد الخصم).
- الـ comparator بيرجّع `False` للـ Excel rows لأن الـ current winner عنده `purchase_price` غير NULL.
- **النتيجة:** مفيش Excel target row أبداً بياخد `is_winner=1`.

## ليه ده مشكلة؟

تخيّل صنف بـ 3 عروض:

| Source         | public_price | purchase_price | discount |
|----------------|--------------|----------------|----------|
| Tawreed A      | 150          | 116.13         | 22.5%    |
| Tawreed B      | 145          | 120.00         | 17.2%    |
| Excel target X | **100**      | NULL           | 0%       |

- الـ Excel target X بيقول: "أنا ببيع الكيل ده بـ 100 للعميل النهائي، يعني أنا المخزن الأرخص للعميل."
- لكن الـ pipeline بيشوف: Tawreed A عنده `purchase_price=116.13` (سعر الشراء للصيدلية بعد الخصم). ده الرقم اللي الصيدلي بيدفعه فعلاً للمخزن.
- الصيدلي مش بيشتري من X — هو **بيبيع** للـ X في حالة إن X تاجر جملة. أو العكس: لو X مخزن، الصيدلي بيدفع لـ X بسعر X بيع بيه للناس؟ ده غلط منطقياً.

### لو الـ Excel فعلاً يحوي retail price، يبقى الـ feature محتاجة إعادة فهم:

السؤال المنطقي: **ليه أصاً بنخلّي الـ Excel target ينافس على winner؟**

- الإجابة الحالية في الكود: "لأن الـ winner المفروض يكون الأرخص للـ صيدلي."
- لكن الـ Excel target بيقارن سعر بيع للعميل بسعر شراء الصيدلية — التفاح بالبرتقال.

## الـ impact في الـ UI

في `src/ui/views/run_db/streamlit_run_tables.py:51-114`:

- جدول "Offering stores per item" بيعرض الـ Excel target rows بـ `purchase_price = NULL`.
- مفيش علامة ❌ ولا — بيقول "ده مش سعر شراء، ده سعر بيع للجمهور."
- الـ user بيشوف الـ Excel target row بـ `public_price = 100` ويفتكر إنها "صفقة" وهو في الحقيقة ده السعر اللي الصيدلية بتبيع بيه — مش اللي بيشتري بيه.

## الـ Mapping اللي لازم يتعمل

بما إن الـ Excel يحوي **retail** price والـ Tawreed بيعطي **wholesale** price، عندنا 3 خيارات تصميمية:

### الخيار A: فصل الـ Excel target عن الـ winner competition (الأسلم)

- الـ Excel target يظهر في "Offering stores per item" كـ **reference** بس.
- الـ winner يفضل من Tawreed فقط (أقل `purchase_price`).
- الـ UI يعرض الـ Excel target row تحت header مختلف: `📊 Other pharmacies' retail prices (reference only)`.
- الـ `is_winner` flag ما يتحددش للـ Excel target rows.

✅ آمن منطقياً: بيخلّي كل مصدر يقارن داخل semantic class واحد.
⚠️ الـ Excel target بيبقى "info" مش "competition".

### الخيار B: خلّي الـ Excel target ينافس لكن بـ apples-to-apples

- لو الـ Excel يحوي retail price، حوّله لـ purchase price بـ heuristic (مثلاً: `purchase_price_est = retail_price * (1 - avg_discount)`).
- الـ winner competition تستخدم `purchase_price` بس — فالـ Excel target بيكسب لو الـ heuristic أقل.
- وضّح في الـ UI: `📊 Excel target (purchase price estimated from retail)`.

⚠️ الـ heuristic مش reliable — ممكن يطلع غلط.
✅ بيدّي الـ Excel target فرصة يفوز.

### الخيار C: أضف عمودين في الـ Excel (لو المخزن بيوفر الاتنين)

- لو الـ Excel فيه سعر شراء وسعر بيع، نخلّي الـ user يحدد كل عمود في الـ config:
  ```yaml
  excel_targets:
    my_store:
      name_col: "اسم الصنف"
      public_price_col: "سعر البيع"      # سعر بيع الصيدلية للجمهور
      purchase_price_col: "سعر الشراء"   # سعر شراء الصيدلية من المخزن
      discount_col: "الخصم"
  ```
- الـ loader بيحط كل رقم في مكانه الصح.
- الـ winner يقارن `purchase_price` من المصدرين (Tawreed والـ Excel target) بشكل صح.

✅ الـ semantic صح 100%.
⚠️ بيعتمد إن المخزن فعلاً عنده العمودين في الـ Excel.

## اللي بنصح بيه

**الخيار A** كـ default safety، مع **الخيار C** كـ future enhancement لما الـ Excel يحوي العمودين.

التطبيق المفصّل في [`05_recommendations.md`](./05_recommendations.md).

## التوضيح الـ naming convention confusion

من `docs/order_runs_sqlite/07_risks_and_decisions.md:63-82`:

```
"winner_sale_price":     public_price,   # ← من retailPrice/publicPrice
"winner_Purchase_Price": sales_price,    # ← من salePrice/salesPrice
```

> ⚠️ الـ naming في الـ schema مقلوب الحدس: `winner_sale_price` بيستخدم `public_price` (مش سعر الشراء)، و `winner_Purchase_Price` بيستخدم `salePrice` (اللي هو سعر الشراء الفعلي). الـ audit في `07_risks_and_decisions.md:63-68` بيناقش ده صراحةً.

ده confusion قديم في الـ project — مفروض نعالجه في يوم من الأيام بس مش لازم دلوقتي عشان الـ scope.

## الـ takeaways

1. **الـ loader الحالي صح** (لو الـ Excel يحوي retail price زي ما قلت).
2. **الـ winner logic خاطئ في تطبيقه** — بيخلّي الـ Excel target ما بيكسبش.
3. **الـ UI ناقصها توضيح** — لازم label واضح: "retail price (reference only)".
4. **التعليق في `cli_order_excel_target.py:456-461` مغلوط** — لازم يتحدّث.