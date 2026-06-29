# تقرير تحليل مشكلة: عدم تطبيق Manual Review لـ AVIL 6 AMP

**تاريخ التقرير:** 2026-06-22  
**رقم التشغيل المشكل:** 20260622_1535  
**كود الصنف:** 73396  
**اسم الصنف:** AVIL 6 AMP  

---

## 🔴 المشكلة الحقيقية (محدثة)

التصحيح اليدوي **موجود فعلاً** في CockroachDB:
```
Item Code: 73396
Item Name: AVIL 6 AMP
Decision: approved_match
Store Product ID: 2640615
Product Name: AVIL 45.5 MG / 2 ML 6 I.M. AMPS.
Product Name AR: افيل 45.5 مجم / 2 مل 6 امبول
```

**لكن النظام لم يستخدمه!**

---

## 📊 الدليل القاطع

### مقارنة بين صنفين في نفس الـ run:

| الصنف | manual_review_lookup_seconds | النتيجة |
|-------|------------------------------|---------|
| **ACTI-COLLA ADVANCE** | **1.215** | ✅ "Approved by saved manual review (ID match)" |
| **AVIL 6 AMP** | **0.0** | ❌ "No decisive match found" |

**التفسير:**
- `manual_review_lookup_seconds = 1.215` → تم الاتصال بـ CockroachDB بنجاح
- `manual_review_lookup_seconds = 0.0` → **لم يتم** الاتصال أو فشل فوراً

---

## 🔍 تحليل الكود

### الكود المسؤول (`src/core/manual_review_runtime.py`)

```python
def saved_manual_review_decision(item: Item) -> ManualReviewDecision | None:
    """Return a saved manual-review decision."""
    cache = _MANUAL_REVIEW_CACHE.get()
    if cache is not None:
        return cache.lookup(item)
    try:
        return ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup(item.code, item.name)
    except Exception:  # ← المشكلة هنا!
        return None
```

### المشكلة:

**السطر 62-63 يبتلع كل الـ exceptions:**
```python
except Exception:
    return None
```

إذا حدث **أي** خطأ أثناء:
1. الاتصال بـ CockroachDB
2. القراءة من قاعدة البيانات
3. تحليل النتائج

→ يتم **إرجاع `None`** بصمت
→ النظام **يتجاهل** التصحيح اليدوي
→ يكمل بـ matching عادي

---

## 🎯 الأسباب المحتملة (مرتبة حسب الاحتمالية)

### السبب الأول ⭐⭐⭐⭐⭐ (الأكثر احتمالاً)

**فشل الاتصال بـ CockroachDB لهذا الصنف بالتحديد**

**الأدلة:**
- ACTI-COLLA نجح (1.215 ثانية)
- AVIL فشل (0.0 ثانية)
- في نفس الـ run، نفس الجلسة

**السيناريوهات الممكنة:**

#### 1.1 Timeout أو Network Glitch
- الاتصال الأول (ACTI-COLLA) نجح
- الاتصال الثاني (AVIL) timeout أو فشل مؤقتاً
- الـ exception تم ابتلاعه

#### 1.2 Database Lock أو Concurrent Access
- CockroachDB كان مشغولاً بعملية أخرى
- الـ query تم رفضه أو تأخر
- الـ timeout حدث

#### 1.3 Connection Pool Exhausted
- الـ connection pool (max 5 connections) ممتلئ
- لم يكن connection متاح لـ AVIL
- الـ request فشل

---

### السبب الثاني ⭐⭐⭐⭐

**مشكلة في hint_key normalization**

```python
def hint_key(code: str, name: str) -> tuple[str, str]:
    """Return normalized (code, name) for stable lookup."""
    code_key = str(code or "").strip().upper()
    name_key = str(name or "").strip().upper()
    return (code_key, name_key)
```

**السيناريو:**
- التصحيح محفوظ بـ key معين
- الـ lookup يبحث بـ key مختلف قليلاً
- النتيجة: `None` (لم يُعثر عليه)

**مثال:**
- محفوظ: `("73396", "AVIL 6 AMP")`
- البحث: `("73396.0", "AVIL 6 AMP")` أو `("73396", "AVIL  6 AMP")` (مسافتين)

---

### السبب الثالث ⭐⭐⭐

**الترتيب: AVIL جاء قبل ACTI-COLLA في processing**

**السيناريو:**
- عند بداية الـ run، يتم preload كل التصحيحات
- AVIL كان من ضمن الـ preload لكن فشل
- ACTI-COLLA نجح لاحقاً
- الـ cache لم يُبنى بشكل صحيح

---

### السبب الرابع ⭐⭐

**Cache context غير مفعّل أو فارغ**

```python
cache = _MANUAL_REVIEW_CACHE.get()
if cache is not None:
    return cache.lookup(item)
```

**السيناريو:**
- ACTI-COLLA استخدم direct lookup (نجح)
- AVIL استخدم direct lookup لكن فشل
- الـ cache لم يكن مفعّل

---

## 🛠️ الحلول المقترحة

### الحل الأول (عاجل): تحسين Error Handling ⭐⭐⭐⭐⭐

**تعديل `saved_manual_review_decision` لتسجيل الأخطاء:**

```python
import logging
logger = logging.getLogger(__name__)

def saved_manual_review_decision(item: Item) -> ManualReviewDecision | None:
    """Return a saved manual-review decision."""
    cache = _MANUAL_REVIEW_CACHE.get()
    if cache is not None:
        return cache.lookup(item)
    try:
        return ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup(item.code, item.name)
    except Exception as e:
        logger.warning(
            f"Failed to lookup manual review for {item.code}/{item.name}: {type(e).__name__}: {e}"
        )
        return None
```

**الفائدة:**
- نكتشف السبب الحقيقي للفشل
- نستطيع تصحيح المشكلة

---

### الحل الثاني: Retry Logic ⭐⭐⭐⭐

```python
import time

def saved_manual_review_decision(item: Item, max_retries: int = 2) -> ManualReviewDecision | None:
    """Return a saved manual-review decision with retry."""
    cache = _MANUAL_REVIEW_CACHE.get()
    if cache is not None:
        return cache.lookup(item)
    
    for attempt in range(max_retries + 1):
        try:
            return ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup(item.code, item.name)
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Manual review lookup attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(0.05 * (attempt + 1))
            else:
                logger.error(f"Manual review lookup failed after {max_retries + 1} attempts: {e}")
                return None
```

---

### الحل الثالث: Connection Pool Tuning ⭐⭐⭐

**في `src/core/database.py`:**

```python
self.connection_pool = pool.SimpleConnectionPool(
    2,      # Min: 2 (بدلاً من 1)
    10,     # Max: 10 (بدلاً من 5)
    ...
)
```

---

### الحل الرابع: Fallback to Cache All ⭐⭐⭐⭐

**ضمان preload صحيح:**

```python
def preload_manual_review_decisions(items: Iterable[Item]) -> ManualReviewDecisionCache:
    """Load manual-review decisions for this run in one store call."""
    try:
        decisions = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup_many(items)
        logger.info(f"Preloaded {len(decisions)} manual review decisions")
        return ManualReviewDecisionCache(decisions)
    except Exception as e:
        logger.error(f"Failed to preload manual review decisions: {e}")
        return ManualReviewDecisionCache({})
```

---

## 📋 خطة التحقيق والحل

### المرحلة الأولى: التشخيص (15 دقيقة)

**إنشاء سكريبت تشخيصي:**

```python
# diagnose_avil.py
from src.core.manual_review_store import ManualReviewStore
from src.core.manual_review_runtime import saved_manual_review_decision
from src.core.manual_review_hints import hint_key
from src.core.utils.excel import Item
import time

print("=== AVIL Manual Review Diagnosis ===\n")

# Test 1: Direct store lookup
print("1. Direct CockroachDB lookup:")
try:
    store = ManualReviewStore()
    code_key, name_key = hint_key("73396", "AVIL 6 AMP")
    print(f"   Keys: code='{code_key}', name='{name_key}'")
    
    start = time.perf_counter()
    result = store.lookup("73396", "AVIL 6 AMP")
    elapsed = time.perf_counter() - start
    
    if result:
        print(f"   ✓ Found: {result.correct_store_product_id}")
        print(f"   Time: {elapsed:.3f}s")
    else:
        print(f"   ✗ Not found")
        print(f"   Time: {elapsed:.3f}s")
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Runtime lookup
print("\n2. Runtime saved_manual_review_decision:")
try:
    item = Item(code="73396", name="AVIL 6 AMP", qty=1)
    
    start = time.perf_counter()
    result = saved_manual_review_decision(item)
    elapsed = time.perf_counter() - start
    
    if result:
        print(f"   ✓ Found: {result.correct_store_product_id}")
        print(f"   Time: {elapsed:.3f}s")
    else:
        print(f"   ✗ Not found")
        print(f"   Time: {elapsed:.3f}s")
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Compare with working item
print("\n3. Compare with ACTI-COLLA (working):")
try:
    item = Item(code="", name="ACTI-COLLA ADVANCE 10 SACHET", qty=1)
    
    start = time.perf_counter()
    result = saved_manual_review_decision(item)
    elapsed = time.perf_counter() - start
    
    if result:
        print(f"   ✓ Found: {result.correct_store_product_id}")
        print(f"   Time: {elapsed:.3f}s")
    else:
        print(f"   ✗ Not found")
        print(f"   Time: {elapsed:.3f}s")
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")
```

**تشغيل:**
```bash
python diagnose_avil.py
```

---

### المرحلة الثانية: الحل الفوري (30 دقيقة)

**1. تطبيق الحل الأول (Logging):**

```bash
# في src/core/manual_review_runtime.py
# إضافة السطور 1-2 في أول الملف
# تعديل except Exception في saved_manual_review_decision
```

**2. إعادة تشغيل test:**

```bash
python run.py order --profile wardany \
  --excel "test_avil.xlsx" --limit 1
```

**3. فحص الـ logs:**

```bash
# سيظهر:
# WARNING: Failed to lookup manual review for 73396/AVIL 6 AMP: <error details>
```

---

### المرحلة الثالثة: الحل الدائم (1 ساعة)

**1. تطبيق الحل الثاني (Retry):**

```python
# تعديل saved_manual_review_decision
# إضافة retry logic
```

**2. تطبيق الحل الثالث (Connection Pool):**

```python
# في src/core/database.py
# تغيير min=2, max=10
```

**3. اختبار شامل:**

```bash
python run.py order --profile wardany \
  --excel "shortage_report.xlsx" --limit 10
```

---

## 🧪 سكريبت الحل السريع

```python
# quick_fix_manual_review.py
"""
حل سريع: إضافة logging وretry لـ manual review lookup
"""
import logging

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('manual_review_debug.log'),
        logging.StreamHandler()
    ]
)

# التعديل المطلوب في src/core/manual_review_runtime.py:

OLD_CODE = """
def saved_manual_review_decision(item: Item) -> ManualReviewDecision | None:
    cache = _MANUAL_REVIEW_CACHE.get()
    if cache is not None:
        return cache.lookup(item)
    try:
        return ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup(item.code, item.name)
    except Exception:
        return None
"""

NEW_CODE = """
def saved_manual_review_decision(item: Item) -> ManualReviewDecision | None:
    cache = _MANUAL_REVIEW_CACHE.get()
    if cache is not None:
        return cache.lookup(item)
    
    # Try up to 3 times
    for attempt in range(3):
        try:
            result = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB).lookup(item.code, item.name)
            if attempt > 0:
                logger.info(f"Manual review lookup succeeded on attempt {attempt + 1} for {item.code}/{item.name}")
            return result
        except Exception as e:
            if attempt < 2:
                logger.warning(f"Manual review lookup attempt {attempt + 1} failed for {item.code}/{item.name}: {e}, retrying...")
                import time
                time.sleep(0.05)
            else:
                logger.error(f"Manual review lookup failed after 3 attempts for {item.code}/{item.name}: {e}")
                return None
"""

print("Apply this change to src/core/manual_review_runtime.py")
print(NEW_CODE)
```

---

## 📌 الخلاصة

### المشكلة الحقيقية:
- **ليست** في matching algorithm
- **ليست** في عدم وجود التصحيح في CockroachDB
- **المشكلة:** فشل الاتصال بـ CockroachDB أثناء lookup لـ AVIL، مع ابتلاع الـ exception

### الدليل:
- `manual_review_lookup_seconds = 0.0` لـ AVIL
- `manual_review_lookup_seconds = 1.215` لـ ACTI-COLLA (نجح)
- في نفس الـ run

### السبب الأرجح:
1. Network timeout مؤقت
2. Connection pool exhaustion
3. Query lock/conflict

### الحل الموصى به:
1. **فوري (15 دقيقة):** إضافة logging للكشف عن الخطأ
2. **سريع (30 دقيقة):** إضافة retry logic (3 محاولات)
3. **دائم (1 ساعة):** تحسين connection pool + error handling شامل

### الأولوية:
🔴 **عاجل:** تشخيص السبب الحقيقي عبر logging  
🟠 **مهم:** إضافة retry mechanism  
🟡 **تحسين:** connection pool tuning  

---

**المحلل:** Kiro AI  
**التاريخ:** 2026-06-22  
**الحالة:** جاهز للتنفيذ
