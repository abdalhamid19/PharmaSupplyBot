# تحسين وظيفة Export-Products - خطة تقنية شاملة

**التاريخ:** 2026-05-09  
**الحالة:** في المرحلة التخطيطية  
**الإصدارات:** Python 3.12.3 | Git 2.43.0  
**المسؤول:** abdalhamid19 (abdalhamid.mahrous@gmail.com)

---

## 📋 البروتوكول الأول: الوعي الزمني ومراجعة الإصدارات

### الإصدارات المستقرة الحالية (حالة الفحص: 2026-05-09)

| المكون | الإصدار | الحالة | ملاحظات |
|--------|--------|-------|--------|
| Python | 3.12.3 | ✅ مستقر | أحدث إصدار LTS |
| Playwright | `requirements.txt` | ✅ محدد | متوافق مع Python 3.12 |
| Pandas | `requirements.txt` | ✅ محدد | لـ Excel I/O |
| Git | 2.43.0 | ✅ مستقر | دعم كامل للـ commits |

---

## 📊 البروتوكول الثاني: التدفق المنطقي - رسم تحليل البيانات

### الحالة الحالية (Current State)

```
POST /rest/v2/product-search
      ↓
[Fetch Page 0..N with lang=ar]
      ↓
[Extract Fields]: 
  - productName (AR)
  - productNameEn (EN)
  - storeProductId
      ↓
[Write to CSV/XLSX/TXT]
      ↓
✅ Export Complete
```

### الحالة المطلوبة (Target State) - المحسّن

```
POST /rest/v2/product-search (langCode: en)
      ↓
[Fetch ALL English-sorted Pages 0..N]
      ↓
[Extract & Store]:
  - productId
  - storeProductId  
  - productNameEn ← SORTED BY ENGLISH
  - productName
  - availableQuantity
  - salePrice ← NEW FIELD
  - discountPercent
  - currency
  - storeName
  - supplierName
      ↓
[Sort in Memory by: productNameEn → productName]
      ↓
POST /rest/v2/product-search (langCode: ar)
      ↓
[Fetch ALL Arabic-sorted Pages 0..N]
      ↓
[Extract & Merge with English results]
      ↓
[Deduplication Phase]:
  - Identity Key: (productNameEn, productName, storeProductId)
  - Remove Duplicates (Keep First Occurrence)
  - Validate No Null Keys
      ↓
[Write Merged+Deduplicated to CSV/XLSX/TXT]
      ↓
✅ Enhanced Export Complete
```

---

## 🏗️ البروتوكول الثالث: المعمارية الذكية - التجريب والتصميم

### المبادئ المعتمدة (من project_guidelines.md)

✅ **Hard Constraints المطبقة:**
- 📏 Maximum line: 100 characters
- 📚 Module docstrings إلزامية
- 🎯 Type hints على APIs العامة
- ⚡ Performance: Data streaming over full loads
- 🧠 Memory: Use generators, not intermediate lists

### المكونات الجديدة المقترحة

#### 1. **Module: `tawreed_product_export_enhanced.py`**
```python
"""Enhanced product-search export with multi-language support."""

def iter_products_alphabetically_sorted(
    page: Page,
    languages: list[str] = None,  # ["en", "ar"]
    page_size: int = 100,
    limit: int = 0,
) -> Iterator[dict[str, Any]]:
    """
    Yield deduplicated products sorted by language priority.
    
    For each language in order:
    1. Fetch all pages with langCode={lang}
    2. Extract fields including salePrice
    3. Stream to deduplication buffer
    4. Sort results by product names
    """
    
def deduplicate_products(
    products: Iterable[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    """
    Yield unique products based on (nameEn, nameAr, storeProductId).
    
    Deduplication Strategy:
    - Use set to track seen identities
    - Keep first occurrence (preserves sort order)
    - Skip null/empty keys
    """
```

#### 2. **Module: `product_export_deduplicator.py`**
```python
"""Deduplication helpers for product exports."""

@dataclass(frozen=True)
class ProductIdentity:
    """Immutable product identity for deduplication."""
    product_name_en: str
    product_name_ar: str
    store_product_id: str
    
def identity_key(product: dict[str, Any]) -> ProductIdentity:
    """Extract dedupe key from product dict."""
    
def deduplicate_by_identity(
    products: Iterable[dict],
) -> list[dict]:
    """Remove duplicates preserving order."""
```

#### 3. **Enhanced Fields in `tawreed_product_export_rows.py`**
```python
EXPORT_FIELDNAMES = (
    "product_name_ar",
    "product_name_en",
    "store_product_id",
    "product_id",  # ← NEW
    "available_quantity",  # ← NEW
    "sale_price",  # ← NEW
    "discount_percent",  # ← NEW
    "currency",  # ← NEW
    "store_name",  # ← NEW
    "supplier_name",  # ← NEW
)
```

---

## 🎯 البروتوكول الرابع: استراتيجية الكود - خطة التنفيذ

### Milestone 1: التحليل والتصميم ✅ (Current)
- [x] قراءة `project_guidelines.md`
- [x] فهم الحالة الحالية
- [x] رسم تدفق البيانات
- [x] تحديد المكونات الجديدة

### Milestone 2: إنشاء المكونات الأساسية
**المدة المتوقعة:** 2-3 ساعات

**المهام:**
- [ ] إنشاء `product_export_deduplicator.py`
- [ ] تحديث `tawreed_product_export_api.py` لدعم langCode
- [ ] تحديث `tawreed_product_export_rows.py` بالحقول الجديدة
- [ ] كتابة اختبارات الوحدة لـ deduplication

**الخطوات:**
```bash
# 1. إنشاء الملف الجديد
touch src/tawreed/product_export_deduplicator.py

# 2. تحديث الحقول
vim src/tawreed/tawreed_product_export_rows.py

# 3. كتابة الاختبارات
touch tests/test_product_export_deduplicator.py

# 4. تشغيل الاختبارات
python -m pytest tests/test_product_export_deduplicator.py -v

# 5. Commit
git add . && git commit -m "feat: Add product deduplicator with enhanced fields"
```

### Milestone 3: تحسين Export Flow
**المدة المتوقعة:** 3-4 ساعات

**المهام:**
- [ ] إنشاء `tawreed_product_export_enhanced.py`
- [ ] دعم البحث متعدد اللغات (EN → AR)
- [ ] تكامل Deduplication
- [ ] اختبار end-to-end

**الخطوات:**
```bash
# 1. إنشاء Module محسّن
touch src/tawreed/tawreed_product_export_enhanced.py

# 2. تحديث export flow
vim src/tawreed/tawreed_product_export_flow.py

# 3. اختبار شامل
python -m pytest tests/test_tawreed_product_export.py -v

# 4. تشغيل export-products يدويًا
python run.py export-products --profile wardany --limit 10

# 5. تحقق من الملفات الناتجة
head -20 artifacts/wardany/tawreed_products.csv
```

### Milestone 4: التحقق والتحسين
**المدة المتوقعة:** 2-3 ساعات

**المهام:**
- [ ] تشغيل `rule_audit.py`
- [ ] التحقق من أن جميع الاختبارات تمر
- [ ] قياس الأداء (Memory + Speed)
- [ ] المراجعة النهائية

**الخطوات:**
```bash
# 1. فحص القواعد
python tools/rule_audit.py

# 2. جميع الاختبارات
python -m pytest tests/ -q

# 3. اختبار تشغيل كامل
python run.py export-products --profile wardany --limit 100

# 4. التحقق من عدم وجود تكرارات
python -c "
import csv
seen = set()
dups = []
with open('artifacts/wardany/tawreed_products.csv') as f:
    for row in csv.DictReader(f):
        key = (row['product_name_en'], row['product_name_ar'], row['store_product_id'])
        if key in seen:
            dups.append(key)
        seen.add(key)
print(f'Total products: {len(seen)}, Duplicates found: {len(dups)}')
"
```

### Milestone 5: التوثيق والنشر
**المدة المتوقعة:** 1-2 ساعات

**المهام:**
- [ ] تحديث `API_RESPONSE_FIELDS.md` بالحقول الجديدة
- [ ] إضافة أمثلة جديدة
- [ ] تحديث README.md إذا لزم الأمر
- [ ] إنشاء PR
- [ ] Merge مع main

**الخطوات:**
```bash
# 1. تحديث الوثائق
vim docs/API_RESPONSE_FIELDS.md

# 2. إضافة التغييرات
git add . && git commit -m "docs: Update API fields for enhanced export"

# 3. دفع التغييرات
git push origin feature/enhanced-export-products

# 4. إنشاء PR على GitHub
# ثم merge بعد المراجعة
```

---

## 🧪 البروتوكول الخامس: استراتيجية الاختبار

### اختبارات الوحدة (Unit Tests)

```python
# tests/test_product_export_deduplicator.py

def test_deduplicate_removes_exact_duplicates():
    """Identical products are deduplicated."""
    
def test_deduplicate_preserves_first_occurrence():
    """First occurrence is kept, later ones removed."""
    
def test_deduplicate_handles_empty_list():
    """Empty list returns empty."""
    
def test_deduplicate_identity_key_construction():
    """ProductIdentity created correctly."""
    
def test_deduplicate_skips_null_keys():
    """Products with null fields are skipped."""
```

### اختبارات التكامل (Integration Tests)

```python
# tests/test_enhanced_export_flow.py

def test_export_fetches_english_first():
    """English language products fetched and sorted first."""
    
def test_export_merges_with_arabic():
    """Arabic products merged with English results."""
    
def test_export_includes_all_new_fields():
    """salePrice, currency, supplier included."""
    
def test_export_deduplicates_across_languages():
    """Products appearing in both EN/AR are deduplicated."""
    
def test_export_maintains_sort_order():
    """Final results sorted by English name then Arabic."""
```

### اختبارات القبول (Acceptance Tests)

```bash
# 1. تشغيل البرنامج
python run.py export-products --profile wardany --limit 50

# 2. التحقق من الملفات
ls -lh artifacts/wardany/tawreed_products.*

# 3. التحقق من الصفوف
wc -l artifacts/wardany/tawreed_products.csv

# 4. التحقق من عدم وجود تكرارات
python validate_export.py artifacts/wardany/tawreed_products.csv
```

---

## 📁 البروتوكول السادس: الذاكرة الخارجية - ARCHITECTURE_MAP.md

### [TECH_STACK]
```
Language: Python 3.12.3
Framework: Playwright (Browser Automation)
Data: pandas (Excel I/O), CSV, JSON
CLI: argparse
Architecture: Layered (Config → Domain → Integration)
```

### [SYSTEM_FLOW - Enhanced Export]
```
1. Auth: Load session from state/<profile>.json
2. Connect: Open browser, authenticate to Tawreed
3. Fetch EN: Paginate product-search API with langCode=en
4. Collect: Stream to deduplicator (no full load)
5. Fetch AR: Repeat with langCode=ar
6. Merge: Combine results, deduplicate
7. Sort: By productNameEn → productName
8. Write: CSV + XLSX + TXT
9. Close: Clean up browser, context, page
```

### [ARCHITECTURE]
```
CLI Layer (run.py)
  ↓
cli/cli_export_products.py
  ↓
tawreed/tawreed_product_export_flow.py (orchestrator)
  ├→ tawreed/tawreed_product_export_api.py (pagination)
  ├→ tawreed/tawreed_product_export_enhanced.py (NEW)
  ├→ tawreed/product_export_deduplicator.py (NEW)
  ├→ tawreed/tawreed_product_export_rows.py (fields)
  └→ tawreed/tawreed_product_export_files.py (output)
```

### [ORPHANS & PENDING]
- [ ] Performance benchmarking (memory usage during fetch)
- [ ] Caching strategy (if needed for repeated exports)
- [ ] Error recovery (resume from page N if connection fails)

---

## ✅ معايير النجاح (Verifiable Goals)

| المعيار | الاختبار | النجاح |
|--------|---------|-------|
| **Completeness** | تصدير 1000+ منتج بدون أخطاء | ✅ كل المنتجات تصدر |
| **Deduplication** | مقارنة EN/AR results | ✅ لا توجد duplicates |
| **Fields** | التحقق من salePrice | ✅ كل صف يحتوي salePrice |
| **Sorting** | التحقق من الترتيب الأبجدي | ✅ مرتب EN → AR |
| **Performance** | قياس الذاكرة | ✅ < 200MB للـ 10k products |
| **Code Quality** | rule_audit + pytest | ✅ 100% passing |

---

## 📝 ملاحظات إضافية

### اتباع القواعس
- ✅ أقل من 100 حرف لكل سطر
- ✅ Docstrings على كل module وfunction
- ✅ Type hints على public APIs
- ✅ Streaming over full loads (Memory efficient)
- ✅ No global state

### استراتيجية الـ Commit
بعد كل Milestone:
```bash
git add .
git commit -m "feat: [Description]"
git push origin feature/enhanced-export-products
```

### التحقق من الجودة
قبل كل push:
```bash
python -m pytest tests/ -q
python tools/rule_audit.py
```

---

## 🚀 الخطوات التالية

**التصرف المطلوب:** ✅ الموافقة على الخطة  
**نقطة البداية:** Milestone 2 - إنشاء المكونات الأساسية  
**المدة الإجمالية المتوقعة:** 8-12 ساعة عمل
