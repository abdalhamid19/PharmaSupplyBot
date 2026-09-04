# 02 — Excel Target source: كيف يدخل الـ Excel للـ pipeline

## شكل الـ config

في `config.example.yaml` قسم `excel_targets` شكله تقريباً:

```yaml
excel_targets:
  my_store:
    name: "Excel Target Demo"
    path: "data/input/excel target/sample.xlsx"
    sheet: "Sheet1"
    header_row: 1
    name_col: "اسم الصنف"
    price_col: "السعر"
    discount_col: "الخصم"
    code_col: "الكود"           # اختياري
```

## كيف يقرأ الـ loader الصفوف؟

`load_target_catalog_from_excel()` في `src/core/excel_target/excel_target_loader.py:72`:

1. يفتح الـ workbook بـ `openpyxl` (read-only).
2. يلاقي الـ header row (سواء بشكل صريح عن طريق `config.header_row` أو عن طريق مسح أول 10 صفوف للبحث عن الـ headers اللي اتعرّفت في الـ config).
3. يحدد numeric indices لكل عمود (`name`, `price`, `discount`, `code`) عن طريق الـ header normalize.
4. لكل صف بعد الـ header:
   - لو مفيش اسم → الصف بيتسقط.
   - لو الكود مش موجود و `requires_code=true` → الصف بيتسقط.
   - يتحوّل لـ `TargetProduct`.

## أهم class: `TargetProduct`

```python
@dataclass(frozen=True)
class TargetProduct:
    code: str
    name: str
    price: float
    discount_percent: float
    source_file: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
```

الـ `price` هنا هو الرقم الوحيد اللي الـ Excel بيوفره عن السعر. **مفيش تمييز** بين retail/public و purchase/sale.

## إزاي `TargetProduct` بيتحوّل لـ candidate dict؟

الـ method `to_candidate_dict()` (`excel_target_loader.py:39`) بتعمل mapping مهم:

```python
return {
    "productNameEn": self.name,
    "productName": self.name,
    "availableQuantity": 1,
    "productsCount": 1,
    "discountPercent": float(self.discount_percent or 0.0),
    "salePrice": float(self.price or 0.0),   # ← هنا المفتاح
    "storeProductId": self.code or ...,
    "excelTarget": True,
    "excelTargetSourceFile": self.source_file,
    "excelTargetRaw": dict(self.raw),
}
```

### لاحظ الـ key: `salePrice`

الـ matcher الأساسي بيقرا `salePrice` كـ **سعر بيع الجمهور (retail price)** في سياق Tawreed — لأن Tawreed بيرجع `salePrice` (اللي هو الجمهور) و `retailPrice` كقيمتين منفصلتين، والـ semantic في `src/tawreed/products` بيخلّي `salePrice` = سعر الجمهور.

لكن في الـ Excel target مفيش سعرين — فيه سعر واحد بس. الـ loader بيحطه في `salePrice` ويخلّي `purchase_price = NULL` (لأنه مش متوفر). ده معناه:

- في `run_item_stores` الـ row اللي جايه من `excel_target` بيكون عنده `public_price` (المأخوذ من `salePrice` كقيمة وحيدة) و `purchase_price = NULL`.

## النتيجة اللي بتشوفها في الـ UI

في `src/cli/commands/cli_order_excel_target.py:458`:

```python
catalogs only carry the pharmacy's purchase price + discount + name, so
the public/retail price is left empty and the warehouse identity is
```

ده كلام موجود داخل الكود بيقول إن الـ loader معامل الـ Excel كأنه يحتوي **سعر شراء الصيدلية** (purchase_price) مش سعر بيع الجمهور. لكن فعلياً الـ key اللي بيتملى هو `salePrice`، وده الـ semantic الذي يتعامل بيه الـ matcher.

### يعني فيه عدم اتساق دلالي (semantic mismatch):

- **التوثيق في الكود**: يقول إن الـ Excel يحوي سعر الشراء (purchase).
- **الـ behavior الفعلي**: الرقم يدخل كـ `salePrice` ويُعرض تحت `public_price` (في `run_item_stores`)، ويكون `purchase_price = NULL`.

## الفرق بين الـ sources في candidate dict

في `cli_order_excel_target.py:470-482`:

```python
price = best.get("salePrice", best.get("price", 0)) or 0
...
"salePrice": float(price),
"sellingPrice": float(price),
"publicPrice": float(price),     # ← populated here (تقدر تتأكد من الكود)
"availableQuantity": 1,
"discountPercent": ...,
```

بينما `cli_order.py` للـ Tawreed بيدخل الاثنين:

```python
"public_price":   retailPrice,    # للجمهور
"purchase_price": salePrice,      # اللي الصيدلي بيدفعه
```

عشان كده في جدول `run_item_stores` لما يكون مصدر الصف `excel_target` بتشوف عمود `purchase_price` فاضي — لأن الـ Excel أصلاً مبيوفرش غير رقم واحد.