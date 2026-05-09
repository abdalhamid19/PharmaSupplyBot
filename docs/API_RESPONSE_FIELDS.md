# حقول API استجابة Tawreed Product Search

## نقطة النهاية (Endpoint)

```
POST https://api.tawreed.io/rest/v2/product-search?sort=productName,asc&page={page}&size={size}
```

## جسم الطلب (Request Body)

```json
{
  "mode": "error",
  "langCode": "ar",
  "data": {
    "displayType": 1
  }
}
```

---

## 📋 حقول الاستجابة (Response Fields)

### 1️⃣ **معلومات المنتج الأساسية**

| الحقل | النوع | الوصف |
|------|------|-------|
| `productId` | `int` | معرف فريد للمنتج في نظام Tawreed |
| `storeProductId` | `string` | معرف الصنف في متجر معين (يختلف لكل متجر) |
| `productName` | `string` | اسم المنتج بالعربية |
| `productNameEn` | `string` | اسم المنتج بالإنجليزية |
| `productNameEnFallback` | `string` | اسم إنجليزي بديل في حالة عدم توفر الاسم الأساسي |
| `productNameEnSynthetic` | `string` | اسم إنجليزي تم توليده من البيانات (من DOM عند فشل API) |

**مثال:**
```json
{
  "productId": 12345,
  "storeProductId": "store-67890",
  "productName": "باراسيتامول 500 ملغ",
  "productNameEn": "Paracetamol 500mg",
  "productNameEnFallback": "Para 500",
  "productNameEnSynthetic": ""
}
```

---

### 2️⃣ **معلومات التوفرية والكمية**

| الحقل | النوع | الوصف |
|------|------|-------|
| `availableQuantity` | `int` | الكمية المتاحة حاليًا في المخزن |
| `productsCount` | `int` | إجمالي عدد المنتجات (قد يكون مختلفًا عن available) |
| `stockLevel` | `int/string` | مستوى المخزون (منخفض، عالي، وسط) |

**مثال:**
```json
{
  "availableQuantity": 250,
  "productsCount": 250,
  "stockLevel": "متوفر"
}
```

---

### 3️⃣ **معلومات التسعير والخصم**

| الحقل | النوع | الوصف |
|------|------|-------|
| `retailPrice` | `float/string` | السعر الجملة (wholesale price) |
| `salePrice` | `float/string` | سعر البيع بالتجزئة (retail price) |
| `discountPercent` | `float/string` | نسبة الخصم المئوية |
| `currency` | `string` | رمز العملة (عادة: "SAR", "AED", إلخ) |

**مثال:**
```json
{
  "retailPrice": 5.50,
  "salePrice": 7.99,
  "discountPercent": 31.0,
  "currency": "SAR"
}
```

---

### 4️⃣ **معلومات المتجر والمورد**

| الحقل | النوع | الوصف |
|------|------|-------|
| `storeName` | `string` | اسم المتجر أو الفرع |
| `supplierName` | `string` | اسم المورد (الشركة الموردة) |

**مثال:**
```json
{
  "storeName": "فرع الرياض الرئيسي",
  "supplierName": "شركة الدواء للتوزيع"
}
```

---

### 5️⃣ **معلومات الطلب والأولويات**

| الحقل | النوع | الوصف |
|------|------|-------|
| `priority` | `int/string` | أولوية المنتج في النتائج |
| `minOrderDiff` | `int` | الفرق بين الحد الأدنى للطلب والكمية المطلوبة |

**مثال:**
```json
{
  "priority": 1,
  "minOrderDiff": 0
}
```

---

### 6️⃣ **معلومات الصور والمحتوى**

| الحقل | النوع | الوصف |
|------|------|-------|
| `imageContentId` | `string` | معرف صورة المنتج في نظام CDN |

**مثال:**
```json
{
  "imageContentId": "img-content-98765"
}
```

---

## 📊 أمثلة حقيقية للمنتجات

### مثال 1️⃣: بنادول إكسترا

```json
{
  "productId": 99,
  "storeProductId": 1001,
  "productName": "بنادول اكسترا 24 قرص",
  "productNameEn": "Panadol Extra 24 Tabs",
  "productNameEnFallback": "",
  "productNameEnSynthetic": "",
  "availableQuantity": 12,
  "productsCount": 12,
  "stockLevel": "متوفر",
  "storeName": "فرع الرياض الرئيسي",
  "supplierName": "شركة الدواء للتوزيع",
  "discountPercent": 31,
  "retailPrice": 14.0,
  "salePrice": 20.5,
  "currency": "SAR",
  "priority": 1,
  "minOrderDiff": 0,
  "imageContentId": "img-content-panadol-001"
}
```

**الاستخدام:**
- كود المنتج: `123`
- الاسم المطلوب: `Panadol Extra`
- الكمية المطلوبة: `2`
- الكمية المتاحة: `12` ✅ (كافية)
- الخصم: `31%` 💰

---

### مثال 2️⃣: ديفارول (متعدد المخازن)

**من المخزن الأول:**
```json
{
  "productId": 456,
  "storeProductId": "store-1",
  "productName": "ديفارول 200 مل",
  "productNameEn": "Devarol 200ml",
  "availableQuantity": 2,
  "storeName": "First Store",
  "discountPercent": 20,
  "salePrice": 15.75,
  "currency": "SAR"
}
```

**من المخزن الثاني:**
```json
{
  "productId": 456,
  "storeProductId": "store-2",
  "productName": "ديفارول 200 مل",
  "productNameEn": "Devarol 200ml",
  "availableQuantity": 5,
  "storeName": "Second Store",
  "discountPercent": 30,
  "salePrice": 14.50,
  "currency": "SAR"
}
```

**القرار (بناءً على استراتيجية max_discount):**
- اختيار المخزن الثاني (خصم أعلى 30%)
- الكمية: `5`
- الملخص: `"30% (qty 5)"` 💎

---

### مثال 3️⃣: E MOX 500 MG CAP

```json
{
  "productId": 789,
  "storeProductId": "dom-row-emox",
  "productName": "إي موكس 500 ملغ",
  "productNameEn": "E MOX 500 MG CAP",
  "productNameEnSynthetic": "",
  "availableQuantity": 25,
  "productsCount": 25,
  "storeName": "شركه ابو عميره (الجيزه)",
  "supplierName": "شركه ابو عميره (الجيزه)",
  "discountPercent": "40.5",
  "salePrice": 12.99,
  "currency": "EGP"
}
```

**الملخص:**
- تم البحث: `E MOX 500 MG CAP`
- الكمية المطلوبة: `3`
- الخصم المسجل: `"40.5%"` 🎯
- اسم المورد: `"شركه ابو عميره (الجيزه)"`

---

## 🔄 هيكل استجابة API الكاملة

```json
{
  "data": {
    "page": 0,
    "totalPages": 25,
    "totalElements": 2500,
    "content": [
      { /* منتج 1 */ },
      { /* منتج 2 */ },
      { /* ... */ }
    ]
  }
}
```

| الحقل | النوع | الوصف |
|------|------|-------|
| `page` | `int` | رقم الصفحة الحالية (بدءًا من 0) |
| `totalPages` | `int` | إجمالي عدد الصفحات |
| `totalElements` | `int` | إجمالي عدد المنتجات |
| `content` | `array` | مصفوفة المنتجات |

---

## 💾 كيفية استخدام هذه البيانات

### في `export-products`
يتم استخراج الحقول التالية إلى CSV/XLSX/TXT:
- `product_name_ar` ← `productName`
- `product_name_en` ← `productNameEn`
- `store_product_id` ← `storeProductId`
- `product_id` ← `productId`
- `available_quantity` ← `availableQuantity`
- `sale_price` ← `salePrice`
- `discount_percent` ← `discountPercent`
- `currency` ← `currency`
- `store_name` ← `storeName`
- `supplier_name` ← `supplierName`

### في `--match-only`
يتم استخراج جميع الحقول المذكورة أعلاه ودمجها مع:
- نتائج المطابقة والدرجات
- سبب القبول/الرفض
- نسخة JSON كاملة مضغوطة

### في DOM Fallback
عند فشل API، يتم:
1. استخراج البيانات من الجدول DOM
2. إضافة بادئة `dom-row-` إلى `storeProductId`
3. ملء `productNameEnSynthetic` من النصوص المرئية

---

## 🚀 ملاحظات مهمة

1. **التصفح**: يتم جلب البيانات صفحة تلو الأخرى بحجم محدد (افتراضيًا 100)
2. **نطاق التصدير**: يتم جلب الصفحات العامة ثم بحث `A-Z` ثم الحروف العربية
3. **الفريدية**: يتم حذف التكرارات بناءً على `(productName, productNameEn, storeProductId)`
4. **الخطأ**: إذا كانت `availableQuantity = 0`، فقد يكون المنتج غير متاح
5. **الترتيب**: النتائج تحفظ بأولوية العام ثم الإنجليزي ثم العربي
6. **الرؤوس**: قد تحتاج بعض الطلبات إلى `Authorization` و `X-*` headers
