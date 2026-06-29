# تقرير إصلاح مشكلة min_discount_percent

**التاريخ:** 2026-06-26  
**المشروع:** PharmaSupplyBot  
**المشكلة:** min_discount_percent=30 لكن قُبل منتج بخصم 27%

---

## 1. وصف المشكلة

**الإعدادات:**
- `min_discount_percent: 30`
- `warehouse_mode: "max_discount"`

**المنتج المبلغ عنه:**
- الاسم: LIMITLESS MAN MAX 100 TABS
- الخصم: **27%**
- storeProductId: 2805824
- الكمية: 89

**السلوك الفعلي:** تم قبول المنتج وإضافته للسلة ✗  
**السلوك المتوقع:** يجب رفض المنتج لأن 27% < 30% ✓

---

## 2. التحقيق والتحليل

### 2.1 فحص تدفق البيانات

#### ✅ قراءة من GUI
```python
# streamlit_order_form.py
min_discount = st.number_input("Minimum discount percent", ...)
```
**النتيجة:** يعمل بشكل صحيح

#### ✅ تمرير عبر CLI
```python
# streamlit_order.py
command.extend(["--min-discount-percent", f"{min_discount_percent:g}"])
```
**النتيجة:** يعمل بشكل صحيح

#### ✅ تطبيق على Config
```python
# cli_order.py
app_config.warehouse_strategy["min_discount_percent"] = float(min_discount_percent)
```
**النتيجة:** يعمل بشكل صحيح

#### ✅ منطق التصفية (Multi-store)
```python
# tawreed_store_selection.py
if choice.discount_percent >= min_discount_percent - 0.001
```
**النتيجة:** يعمل بشكل صحيح

### 2.2 اختبار إعادة الإنتاج

```python
stores = [{"discountPercent": 27.0, "availableQuantity": 89}]
choice = choose_next_store_for_remaining_quantity(stores, set(), "max_discount", RuntimeError, 30.0)
# Result: REJECTED ✓
```

**الاستنتاج:** المنطق الأساسي يعمل! إذن أين المشكلة؟

---

## 3. السبب الجذري

### 3.1 اكتشاف المشكلة

هناك **مساران** لإضافة المنتجات:

**أ. Multi-Store Products (منتجات متعددة المخازن):**
```python
if is_multi:
    return add_item_from_store_dialogs(...)  # ← يفحص min_discount ✓
```

**ب. Single-Store Products (منتج بمخزن واحد):**
```python
_click_cart(bot, row, item, match)  # ← لا يفحص! ✗
```

### 3.2 الكود المسبب للمشكلة

**قبل الإصلاح:**
```python
def _click_cart(bot, row, item, match):
    from .tawreed_store_summary import record_single_store
    
    record_single_store(bot, match.data)
    wait_for_row_to_settle(row)
    cart_button(row).click()  # ← إضافة مباشرة بدون فحص!
```

**نفس المشكلة في API mode:**
```python
def _add_single_item_to_cart(bot, api, match, item, record_timing):
    api.add_to_cart(match, int(item.qty))  # ← إضافة مباشرة!
```

### 3.3 التشخيص النهائي

🎯 **السبب:** المنتجات ذات المخزن الواحد (single-store) لا يتم فحص `min_discount_percent` عليها!

**منتج LIMITLESS MAN MAX كان:**
- متوفر في مخزن واحد فقط
- تم تصنيفه كـ single-store
- تم تجاوز فحص الخصم
- تمت الإضافة للسلة مباشرة

---

## 4. الحل المطبق

### 4.1 التعديل الأول: Browser Mode

**الملف:** `src/tawreed/tawreed_products_flow.py`

```python
def _click_cart(bot, row, item, match):
    from .tawreed_store_summary import record_single_store
    from .tawreed_pricing import discount_value_as_percent, first_discount_value
    
    # Check min_discount_percent for single-store products
    min_discount = _min_disc(bot)
    if min_discount > 0:
        store_discount = discount_value_as_percent(first_discount_value(match.data))
        if store_discount < min_discount - 0.001:
            raise bot.skip_item_exception(
                f"Store discount ({store_discount:g}%) is below minimum ({min_discount:g}%)."
            )
    
    record_single_store(bot, match.data)
    wait_for_row_to_settle(row)
    cart_button(row).click()
```

### 4.2 التعديل الثاني: API Mode

**الملف:** `src/tawreed/tawreed_api_flow.py`

```python
def _add_single_item_to_cart(bot, api, match, item, record_timing):
    from .tawreed_products_flow import _min_disc
    from .tawreed_pricing import discount_value_as_percent, first_discount_value
    
    # Check min_discount_percent for single-store products
    min_discount = _min_disc(bot)
    if min_discount > 0:
        store_discount = discount_value_as_percent(first_discount_value(match.data))
        if store_discount < min_discount - 0.001:
            raise bot.skip_item_exception(
                f"Store discount ({store_discount:g}%) is below minimum ({min_discount:g}%)."
            )
    
    cart_start = time.perf_counter()
    api.add_to_cart(match, int(item.qty))
    record_timing(bot, "add_to_cart_seconds", time.perf_counter() - cart_start)
    bot.last_ordered_total_qty = int(item.qty)
```

---

## 5. الاختبارات

### 5.1 اختبار جديد

```python
def test_single_store_rejects_below_min_discount(self):
    """Single-store products should reject if discount < min_discount_percent."""
    bot = SimpleNamespace(
        config=SimpleNamespace(warehouse_strategy={"min_discount_percent": 30.0}),
        skip_item_exception=RuntimeError
    )
    match = SimpleNamespace(data={"discountPercent": 27.0})
    
    with self.assertRaises(RuntimeError) as ctx:
        _click_cart(bot, None, None, match)
    
    self.assertIn("27", str(ctx.exception))
    self.assertIn("30", str(ctx.exception))
```

**النتيجة:** ✅ PASSED

### 5.2 جميع الاختبارات

```
Ran 414 tests in 7.806s
OK
```

✅ **جميع الاختبارات نجحت**

---

## 6. التحقق من الحل

### 6.1 سيناريو المشكلة الأصلية

| الحالة | min | store | النتيجة |
|--------|-----|-------|---------|
| قبل الإصلاح | 30% | 27% | ACCEPTED ✗ |
| بعد الإصلاح | 30% | 27% | REJECTED ✓ |

### 6.2 سيناريوهات شاملة

| min | store | نوع | النتيجة المتوقعة | الفعلي |
|-----|-------|------|------------------|--------|
| 30% | 27% | Single | REJECTED | ✅ REJECTED |
| 30% | 35% | Single | ACCEPTED | ✅ ACCEPTED |
| 30% | 27% | Multi | REJECTED | ✅ REJECTED |
| 30% | 35% | Multi | ACCEPTED | ✅ ACCEPTED |
| 0% | 10% | Single | ACCEPTED | ✅ ACCEPTED |

---

## 7. الملخص

### 7.1 المشكلة
منتجات المخزن الواحد لا يتم فحص `min_discount_percent` عليها

### 7.2 الحل
إضافة فحص الخصم في `_click_cart` و `_add_single_item_to_cart`

### 7.3 النتيجة
- ✅ تم إصلاح المشكلة
- ✅ جميع الاختبارات نجحت
- ✅ السلوك صحيح في جميع الحالات

---

**تم الإعداد:** 2026-06-26  
**الحالة:** ✅ مكتمل ومُختبَر
