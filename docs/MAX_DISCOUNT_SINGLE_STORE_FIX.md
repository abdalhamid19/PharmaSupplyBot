# تقرير سلوك max_discount mode مع tolerance

**التاريخ:** 2026-06-26  
**المشروع:** PharmaSupplyBot  
**الملفات المعدلة:** 
- `src/tawreed/tawreed_products_flow.py`
- `src/tawreed/tawreed_api_flow.py`

---

## 1. ملخص تنفيذي

تم تعديل سلوك وضع `max_discount` (Highest discount only) ليطلب من **جميع المخازن** التي لديها أعلى خصم أو قريبة منه (فرق أقل من 0.5%) حتى تكتمل الكمية المطلوبة.

**السلوك:**
- ✅ يبحث عن أعلى نسبة خصم متاحة
- ✅ يقبل أي مخزن بخصم ضمن 0.5% من الأعلى
- ✅ يتحقق من min_discount_percent قبل البدء
- ✅ يستمر حتى تكتمل الكمية أو تنتهي المخازن المقبولة

---

## 2. المتطلبات

### السلوك المطلوب

```yaml
warehouse_strategy:
  mode: "max_discount"
  min_discount_percent: 12
```

**القواعد:**
1. إيجاد أعلى نسبة خصم بين المخازن المتاحة
2. إذا كان أعلى خصم < 12%: رفض الصنف فوراً
3. قبول أي مخزن بخصم ضمن **0.5%** من الأعلى
4. الاستمرار حتى تكتمل الكمية أو تنتهي المخازن المقبولة

### أمثلة

#### مثال 1: مخازن متقاربة

```
stores: [A: 10@25%, B: 8@24.8%, C: 15@24.6%, D: 20@20%]
max_discount = 25%
tolerance = 0.5%

acceptable stores:
- A: 25% (max)
- B: 24.8% (diff = 0.2% < 0.5%) ✓
- C: 24.6% (diff = 0.4% < 0.5%) ✓  
- D: 20% (diff = 5% > 0.5%) ✗

needed: 30 units
result: Order from A(10) + B(8) + C(12) = 30 units
```

#### مثال 2: مخزن واحد كافٍ

```
stores: [A: 50@25%, B: 30@20%]
max_discount = 25%

acceptable stores:
- A: 25% (max) ✓
- B: 20% (diff = 5% > 0.5%) ✗

needed: 30 units
result: Order 30 units from A only
```

#### مثال 3: رفض لعدم تحقيق الحد الأدنى

```
stores: [A: 10@10%, B: 8@9%]
max_discount = 10%
min_discount_percent = 12%

result: Item REJECTED (10% < 12%)
```

---

## 3. التعديلات التقنية

### 3.1 في `tawreed_products_flow.py`

```python
# In max_discount mode, only use stores within 0.5% of max discount
if mode == "max_discount" and max_discount_value is not None:
    if choice.discount_percent < max_discount_value - 0.5:  # ← 0.5% tolerance
        break
```

### 3.2 في `tawreed_api_flow.py`

نفس المنطق للـ API mode.

### 3.3 التحقق المبكر من min_discount

```python
if mode == "max_discount" and store_rows:
    max_discount_value = _find_max_discount(store_rows)
    min_discount = _min_disc(bot)
    if max_discount_value < min_discount - 0.001:
        raise bot.skip_item_exception(
            f"Highest discount ({max_discount_value:g}%) is below minimum ({min_discount:g}%)."
        )
```

---

## 4. جدول السلوك

| Max Discount | Store Discount | Diff | Accept? |
|--------------|----------------|------|---------|
| 25% | 25.0% | 0.0% | ✓ |
| 25% | 24.9% | 0.1% | ✓ |
| 25% | 24.5% | 0.5% | ✓ (حد) |
| 25% | 24.4% | 0.6% | ✗ |
| 25% | 20.0% | 5.0% | ✗ |

---

## 5. الاختبارات

✅ 9 اختبارات ناجحة تغطي:
- إيجاد أعلى خصم
- اختيار المخازن المقبولة
- رفض عند عدم تحقيق الحد الأدنى
- التعامل مع مخازن متعددة بنفس الخصم

---

## 6. الخلاصة

**السلوك النهائي:**
- في وضع `max_discount`: يطلب من المخازن ذات أعلى خصم ± 0.5%
- يضمن جودة الصفقة مع مرونة معقولة (0.5%)
- يحترم min_discount_percent كحد أدنى مطلق

**الفائدة:**
- التوازن بين الجودة (أعلى خصم) والكمية (إكمال الطلب)
- مرونة لاستيعاب فروق بسيطة بين المخازن
- سلوك واضح ومتوقع
