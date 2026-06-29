# تقرير شامل: مشكلة matched_product_name_en في Browser Mode

## 📋 وصف المشكلة

### الوضع الحالي

✅ **في API Execution Mode**: تم حل المشكلة، `matched_product_name_en` يظهر بشكل صحيح  
❌ **في Browser Execution Mode**: المشكلة لا تزال موجودة، `matched_product_name_en` فارغ

### التفاصيل

عند تشغيل order run في Browser mode، إذا كان status الصنف `not-orderable`:
- ✅ `matched_product_name_ar` **يظهر** (الاسم العربي)
- ❌ `matched_product_name_en` **فارغ** (الاسم الإنجليزي)
- ✅ `blocked_candidate_name_ar` **يظهر**
- ❌ `blocked_candidate_name_en` **فارغ**

---

## 🔍 مثال حقيقي من Browser Mode

### من ملف: `order_item_summary.csv` (Browser mode)

```csv
item_code: 74821
item_name: BETADINE ANTISEPTIC 60 ML SOLN. 10%
status: not-orderable

# ✅ موجود
matched_product_name_ar: بيتادين محلول مطهر 10 % 60 مل

# ❌ فارغ
matched_product_name_en: 

# ✅ موجود
blocked_candidate_name_ar: بيتادين محلول مطهر 10 % 60 مل

# ❌ فارغ
blocked_candidate_name_en: 
```

### مقارنة: نفس الصنف في API Mode

```csv
item_code: 74821
item_name: BETADINE ANTISEPTIC 60 ML SOLN. 10%
status: not-orderable

# ✅ موجود
matched_product_name_ar: بيتادين محلول مطهر 10 % 60 مل النيل

# ✅ موجود
matched_product_name_en: BETADINE ANTISEPTIC SOLN. 10 % 60 ML

# ✅ موجود
blocked_candidate_name_ar: بيتادين محلول مطهر 10 % 60 مل النيل

# ✅ موجود
blocked_candidate_name_en: BETADINE ANTISEPTIC SOLN. 10 % 60 ML
```

---

## 🔬 التحليل التفصيلي الممل

### 1. الفرق بين API Mode و Browser Mode

#### API Mode (يعمل ✅)

```
[User Search]
    ↓
[API Call to Tawreed]
    ↓
[JSON Response with complete data]
    ↓
{
  "productId": 1914,
  "productName": "بيتادين محلول مطهر 10 % 60 مل النيل",      ← Arabic
  "productNameEn": "BETADINE ANTISEPTIC SOLN. 10 % 60 ML",  ← English ✓
  "storeProductId": "...",
  "availableQuantity": 0
}
```

#### Browser Mode (مشكلة ❌)

```
[User Search]
    ↓
[Browser renders table]
    ↓
[DOM Scraping from HTML]
    ↓
{
  "productName": "بيتادين محلول مطهر 10 % 60 مل",           ← من DOM ✓
  "productNameEn": "",                                      ← فارغ! ❌
  "productNameEnFallback": "BETADINE-ANTISEPTIC-SOLN...",  ← synthetic
  "productNameEnSynthetic": true,
  "storeProductId": "dom-row-..."
}
```


---

## 🐛 السبب الجذري للمشكلة

### الموقع: `src/tawreed/tawreed_dom_fields.py:17-19`

```python
def _dom_candidate(lines, query: str, s_count: int, c_count: int, row) -> dict[str, Any]:
    return {
        "productNameEn": "",  # ← دائماً فارغ! ❌
        "productNameEnFallback": fallback_english_name(query, lines[0]),  # ← synthetic
        "productNameEnSynthetic": True,  # ← علامة أنه مُولّد
        "productName": lines[0],  # ← من DOM، عربي ✓
        # ...
    }
```

### الشرح:

**المشكلة الأساسية:**
عندما يفشل API أو لا يرجع نتائج كافية، النظام يعتمد على **DOM scraping** كـ fallback.

**ماذا يحدث في DOM scraping؟**

1. **يقرأ الجدول المرئي من HTML**
2. **يستخرج الأسطر المرئية** (عربي فقط)
3. **يبني candidate بدون اسم إنجليزي**

**لماذا لا يوجد اسم إنجليزي في DOM؟**

لأن **واجهة Tawreed لا تعرض الاسم الإنجليزي في الجدول!**

---

## 🔍 الأسباب المحتملة (كلها)

### السبب #1: DOM لا يحتوي على productNameEn ✅ **الأساسي**

**الدليل:**
```python
# src/tawreed/tawreed_dom_fields.py:18
"productNameEn": "",  # ← hard-coded empty string
```

**الترجيح:** 95%

---

### السبب #2: candidate_summary_fields لا يستخدم Fallback 🔶

**الموقع:** `src/core/order_winner_fields.py:12`

```python
def candidate_summary_fields(candidate: dict, decision, match) -> dict[str, object]:
    return {
        "matched_product_name_en": candidate.get("productNameEn", ""),  # ← فقط productNameEn
        "matched_product_name_ar": candidate.get("productName", ""),
    }
```

**المشكلة:**
```python
candidate = {
  "productNameEn": "",  # ← فارغ
  "productNameEnFallback": "BETADINE-ANTISEPTIC-60-ML",  # ← موجود لكن غير مستخدم!
}

matched_product_name_en = candidate.get("productNameEn", "")  # = "" ❌
```

**الترجيح:** 80%


---

## ✅ الحلول الممكنة (كلها)

### الحل #1: استخدام productNameEnFallback في matched_product_name_en ⭐⭐⭐ **الأفضل**

**الملف:** `src/core/order_winner_fields.py`

```python
def candidate_summary_fields(candidate: dict, decision, match) -> dict[str, object]:
    """Return matched-candidate and winner fields for summary artifacts."""
    candidate_id = candidate_store_product_id(candidate)
    
    # Use fallback for English name if primary is empty
    en_name = (
        candidate.get("productNameEn") 
        or candidate.get("productNameEnFallback") 
        or ""
    )
    
    return {
        "matched_product_name_en": en_name,  # ← FIX
        "matched_product_name_ar": candidate.get("productName", ""),
        "matched_product_id": candidate.get("productId", ""),
        "matched_store_product_id": candidate_id,
        # ...
    }
```

**الفوائد:**
- ✅ يحل المشكلة في كل الحالات
- ✅ يستخدم الاسم الحقيقي إذا موجود من API
- ✅ يستخدم Fallback إذا جاء من DOM
- ✅ لا يغير المنطق الأساسي

**العيوب:**
- ⚠️ Fallback اصطناعي (ليس من Tawreed)
- ⚠️ قد لا يطابق النموذج الرسمي

**التقييم:** 9/10

---

### الحل #2: تطبيق نفس المنطق في blocked_candidate_fields ⭐⭐

**الملف:** `src/core/order_blocked_candidate.py`

```python
def blocked_candidate_fields(candidate: dict) -> dict[str, object]:
    """Return blocked-candidate fields for summary artifacts."""
    return {
        "blocked_candidate_name_en": (
            candidate.get("productNameEn") 
            or candidate.get("productNameEnFallback") 
            or ""
        ),
        "blocked_candidate_name_ar": candidate.get("productName", ""),
        # ...
    }
```

**الفوائد:**
- ✅ اتساق مع matched fields
- ✅ يملأ blocked_candidate_name_en أيضاً

**التقييم:** 8/10

---

### الحل #3: استخراج productNameEn من DOM إذا أمكن ⭐ **صعب**

**الفكرة:**
محاولة إيجاد الاسم الإنجليزي في عناصر HTML غير مرئية.

```python
def _dom_candidate(lines, query: str, s_count: int, c_count: int, row):
    # Try to extract English name from hidden elements
    en_name = _try_extract_english_name(row)
    
    return {
        "productNameEn": en_name or "",
        "productNameEnFallback": fallback_english_name(query, lines[0]),
        # ...
    }
```

**المشاكل:**
- ❌ قد لا يوجد الاسم في HTML أصلاً
- ❌ يزيد تعقيد DOM scraping
- ❌ غير موثوق

**التقييم:** 4/10

---

### الحل #4: إجبار API mode دائماً ❌ **غير عملي**

**الفكرة:**
عدم استخدام DOM fallback أبداً.

**المشاكل:**
- ❌ يفقد النتائج عند فشل API
- ❌ يقلل معدل النجاح
- ❌ DOM fallback موجود لسبب

**التقييم:** 2/10

---

### الحل #5: تحسين fallback_english_name ⭐⭐ **إضافي**

**الملف:** `src/tawreed/tawreed_dom_fallback.py`

```python
def fallback_english_name(query: str, arabic_name: str) -> str:
    """Generate better English name from query and Arabic."""
    # Current: simple normalization
    # Improvement: use query as base if it's already English
    
    if _is_mostly_english(query):
        return _normalize_english(query)
    
    return _normalize_english(arabic_name)
```

**الفوائد:**
- ✅ أسماء أفضل في Fallback mode
- ✅ يحسن تجربة المستخدم

**العيوب:**
- ⚠️ لا يحل المشكلة الأساسية
- ⚠️ يحتاج logic إضافي

**التقييم:** 7/10


---

## 📊 خطة الحل الكاملة المرتبة

### المرحلة 1: التطبيق السريع (20 دقيقة)

#### الخطوة 1.1: تعديل order_winner_fields.py

```python
# src/core/order_winner_fields.py

def candidate_summary_fields(candidate: dict, decision, match) -> dict[str, object]:
    """Return matched-candidate and winner fields for summary artifacts."""
    candidate_id = candidate_store_product_id(candidate)
    
    # FIX: Use fallback English name for DOM candidates
    en_name = (
        candidate.get("productNameEn") 
        or candidate.get("productNameEnFallback") 
        or ""
    )
    
    return {
        "matched_product_name_en": en_name,
        "matched_product_name_ar": candidate.get("productName", ""),
        "matched_product_id": candidate.get("productId", ""),
        "matched_store_product_id": candidate_id,
        "winner_product_id": candidate.get("productId", ""),
        "winner_store_product_id": candidate_id,
        "winner_available_quantity": candidate.get("availableQuantity", ""),
        "winner_sale_price": candidate.get("salePrice", ""),
        "winner_store_name": candidate.get("storeName", ""),
        "tie_break_reason": _tie_break_reason(decision, match),
    }
```

#### الخطوة 1.2: تعديل order_blocked_candidate.py

```python
# src/core/order_blocked_candidate.py

def blocked_candidate_fields(candidate: dict) -> dict[str, object]:
    """Return blocked-candidate fields for summary artifacts."""
    
    # FIX: Use fallback English name for DOM candidates
    en_name = (
        candidate.get("productNameEn") 
        or candidate.get("productNameEnFallback") 
        or ""
    )
    
    return {
        "blocked_candidate_name_en": en_name,
        "blocked_candidate_name_ar": candidate.get("productName", ""),
        "blocked_candidate_product_id": candidate.get("productId", ""),
        "blocked_candidate_store_product_id": candidate_store_product_id(candidate),
        "blocked_candidate_available_quantity": candidate.get("availableQuantity", ""),
        "blocked_candidate_sale_price": candidate.get("salePrice", ""),
    }
```

---

### المرحلة 2: الاختبار (15 دقيقة)

#### الخطوة 2.1: اختبار Browser mode

```bash
# تشغيل مع أصناف معروفة
python3 run.py order \
  --excel "test_browser.xlsx" \
  --profile wardany \
  --limit 10 \
  --match-only
```

#### الخطوة 2.2: التحقق من النتائج

```python
import pandas as pd

df = pd.read_csv("artifacts/order/wardany/latest/order_item_summary_*.csv")
not_ord = df[df["status"] == "not-orderable"]

print(f"Total not-orderable: {len(not_ord)}")
print(f"With matched_product_name_en: {len(not_ord[not_ord['matched_product_name_en'] != ''])}")
print(f"Success rate: {len(not_ord[not_ord['matched_product_name_en'] != '']) / len(not_ord) * 100:.1f}%")
```

**النتيجة المتوقعة:** 100%

---

### المرحلة 3: التوثيق (10 دقيقة)

#### الخطوة 3.1: إضافة تعليق توضيحي

```python
# في order_winner_fields.py
# NOTE: We use productNameEnFallback for DOM-scraped candidates because
# Tawreed's UI doesn't display English names in the product table.
# The fallback is a normalized version of the query or Arabic name.
```

#### الخطوة 3.2: Commit

```bash
git add src/core/order_winner_fields.py src/core/order_blocked_candidate.py
git commit -m "Fix: use productNameEnFallback for Browser mode DOM candidates

- order_winner_fields: fallback to productNameEnFallback when productNameEn is empty
- order_blocked_candidate: apply same logic for consistency
- Resolves missing matched_product_name_en in Browser execution mode

Issue: Tawreed UI doesn't display English names in product table,
so DOM scraping only captures Arabic names. The fallback provides
a normalized English representation.

Fixes: matched_product_name_en empty for not-orderable in Browser mode"
```

---

## 📈 النتائج المتوقعة

| المقياس | قبل (Browser mode) | بعد (Browser mode) |
|---------|-------------------|-------------------|
| matched_product_name_en موجود | 0% | **100%** |
| matched_product_name_ar موجود | 100% | 100% |
| blocked_candidate_name_en موجود | 0% | **100%** |
| blocked_candidate_name_ar موجود | 100% | 100% |
| وقت التطبيق | - | **20 دقيقة** |

---

## 🎯 الخلاصة

### السبب الأساسي:
`candidate_summary_fields` و `blocked_candidate_fields` يستخدمون فقط `productNameEn` بدون fallback إلى `productNameEnFallback`، بينما DOM candidates لا تحتوي على `productNameEn` (فارغ دائماً).

### الحل الموصى به:
استخدام `productNameEnFallback` كـ fallback في كلا الدالتين.

### الفائدة:
- ✅ matched_product_name_en يظهر دائماً
- ✅ اتساق بين API mode و Browser mode
- ✅ تحسين تجربة المستخدم
- ✅ لا تأثير على API mode (يستمر باستخدام الاسم الحقيقي)

### ملاحظة مهمة:
Fallback name **اصطناعي** (مُولّد من query أو Arabic name)، لكنه أفضل من لا شيء!

