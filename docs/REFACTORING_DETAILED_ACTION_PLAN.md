# خطة العمل التفصيلية للمهام المتبقية (Detailed Action Plan)

**التاريخ:** 28 يونيو 2026  
**الحالة الحالية:** 96.7% نجاح (415/429 اختبار)  
**الهدف:** 100% نجاح + rule_audit_ok

---

## 🔴 المستوى 1: مهام حرجة (يجب إنجازها فوراً)

### 1.1 إصلاح `components_match` - خطر أمان الطلبات

**الأولوية:** 🔴🔴🔴 **حرجة جداً - خطر على صحة الطلبات**  
**التأثير:** خطر طلب أدوية خاطئة (مثلاً VIGOTON PLUS بدلاً من VIGOTON العادي)  
**الوقت المقدّر:** 2-3 ساعات

#### المشكلة بالتفصيل
```python
# الاختبار الفاشل:
test_components_match_rejects_unsafe_matches

# الحالات الثلاث:
1. VIGOTON PLUS 20 TABS ≠ VIGOTON 30 TABS
   - المتوقع: different_modifier
   - الفعلي: different_brand ❌

2. GROWTH FORMULA ADULT CHOCOLATE ≠ GROWTH FORMULA FOR KIDS 400 GM POWDER CHOCOLATE
   - المتوقع: different_age_group
   - الفعلي: different_brand ❌

3. B-FRESH MOUTHWASH MINT ≠ B-FRESH GREEN MOUTH WASH 500 ML
   - المتوقع: different_flavor  
   - الفعلي: different_brand ❌
```

#### السبب الجذري
```
الملف: src/core/drug_matching/normalizer_matching_core.py
الدالة: components_match()

المشكلة: عند التقسيم، تم نقل الدالة من:
  normalizer.py (111 سطر، شامل كل الفحوصات)
إلى:
  normalizer_matching_core.py (56 سطر فقط)

النتيجة: ~55 سطر من منطق الفحوصات الأمنية مفقود
```

#### خطوات الإصلاح
```bash
# 1. استخرج النسخة القديمة الكاملة
git show 6ba97e0~1:src/core/drug_matching/normalizer.py > /tmp/normalizer_old.py

# 2. ابحث عن دالة components_match (السطر ~627، 111 سطر)
grep -n "def components_match" /tmp/normalizer_old.py

# 3. قارن مع النسخة الحالية
code --diff /tmp/normalizer_old.py src/core/drug_matching/normalizer_matching_core.py
```

#### المنطق المطلوب استعادته
```python
# في normalizer_matching_core.py

def components_match(left, right):
    """Check if two drug components match safely."""
    
    # 1. Parse both sides
    left_parsed = parse_drug(left)
    right_parsed = parse_drug(right)
    
    # 2. Check brand name
    if left_parsed.brand != right_parsed.brand:
        return False, "different_brand"
    
    # 3. ✅ CHECK MODIFIERS (المفقود حالياً)
    left_mods = set(left_parsed.modifiers or [])
    right_mods = set(right_parsed.modifiers or [])
    if left_mods != right_mods:
        # Check if it's a known unsafe modifier difference
        unsafe_modifiers = {'PLUS', 'EXTRA', 'FORTE', 'MAX', 'SUPER'}
        if (left_mods - right_mods) & unsafe_modifiers:
            return False, "different_modifier"
        if (right_mods - left_mods) & unsafe_modifiers:
            return False, "different_modifier"
    
    # 4. ✅ CHECK AGE GROUPS (المفقود حالياً)
    age_keywords = {'ADULT', 'KIDS', 'CHILDREN', 'BABY', 'INFANT', 'PEDIATRIC'}
    left_age = {w for w in left_parsed.words if w in age_keywords}
    right_age = {w for w in right_parsed.words if w in age_keywords}
    if left_age != right_age:
        return False, "different_age_group"
    
    # 5. ✅ CHECK FLAVORS (المفقود حالياً)
    flavor_keywords = {'MINT', 'GREEN', 'CHOCOLATE', 'VANILLA', 'STRAWBERRY', 
                       'ORANGE', 'LEMON', 'BERRY'}
    left_flavor = {w for w in left_parsed.words if w in flavor_keywords}
    right_flavor = {w for w in right_parsed.words if w in flavor_keywords}
    if left_flavor != right_flavor:
        return False, "different_flavor"
    
    # 6. Continue with rest of checks...
    # (dosage, form, volume, etc.)
    
    return True, "match"
```

#### ملفات الإصلاح
```
src/core/drug_matching/normalizer_matching_core.py
└─ إضافة الفحوصات الأمنية المفقودة

أو إنشاء ملف جديد:
src/core/drug_matching/normalizer_matching_safety.py
└─ وظائف فحص الأمان (modifiers, age_groups, flavors)
```

#### التحقق
```bash
# تشغيل الاختبار المحدد
py -m unittest tests.test_drug_matching_normalizer.NormalizerTests.test_components_match_rejects_unsafe_matches -v

# يجب أن يمر الثلاث حالات:
# ✅ VIGOTON PLUS ≠ VIGOTON → different_modifier
# ✅ GROWTH ADULT ≠ KIDS → different_age_group
# ✅ B-FRESH MINT ≠ GREEN → different_flavor
```

---

### 1.2 إصلاح Merge Logic في Parallel Match-Only

**الأولوية:** 🔴 **عالية**  
**التأثير:** نتائج match-only غير مدمجة عند التوازي  
**الوقت المقدّر:** 1 ساعة

#### المشكلة
```python
# الاختبار الفاشل:
test_parallel_match_only_merges_match_only_summary

# الخطأ:
AssertionError: Expected 'merge_worker_summaries' to be called once. Called 0 times.
```

#### السبب الجذري
```
عند تشغيل match-only بالتوازي (--item-workers > 1):
- Workers تكتب ملفات منفصلة: match_only_summary.worker_1.csv, worker_2.csv ...
- لكن merge_worker_summaries() لا يُستدعى في نهاية العملية
- النتيجة: الملفات الفرعية تبقى مبعثرة بدون دمج
```

#### خطوات الإصلاح
```bash
# 1. ابحث عن مكان استدعاء merge في order mode
grep -rn "merge_worker_summaries" src/cli/

# 2. تحقق من وجود نفس الاستدعاء في match-only mode
grep -rn "match_only" src/cli/ | grep -i merge

# 3. إذا لم يوجد، أضف الاستدعاء
```

#### الكود المطلوب
```python
# في src/cli/cli_order_single.py أو cli_order_parallel.py

def run_profile_match_only(...):
    # ... existing code ...
    
    # بعد انتهاء workers
    if args.item_workers and args.item_workers > 1:
        # ✅ أضف هذا السطر
        from ..tawreed.order_result_merger import merge_worker_summaries
        merge_worker_summaries(profile_key, "match_only_summary")
```

#### التحقق
```bash
py -m unittest tests.test_cli_commands.CliCommandsTests.test_parallel_match_only_merges_match_only_summary -v
```

---

## 🟡 المستوى 2: مهام متوسطة الأهمية

### 2.1 إصلاح Bot Mocking في API Tests

**الأولوية:** 🟡 **متوسطة**  
**التأثير:** 2 اختبارات API فاشلة  
**الوقت المقدّر:** 30 دقيقة

#### المشكلة
```python
# الاختبار:
test_api_match_only_flow_reuses_one_client_for_all_items

# الخطأ:
AttributeError: '_FlowBot' object has no attribute 'order_flow'
```

#### الحل
```python
# في tests/test_tawreed_api_execution_mode.py

class _FlowBot:
    def __init__(self, config, state_path):
        self.config = config
        self.state_path = state_path
        self.skip_item_exception = _MockException
        
        # ✅ أضف هذه الأسطر
        self.order_flow = Mock()
        self.order_flow.summary_recorder = Mock()
        self.order_flow.summary_recorder.record_match_only_success = Mock()
        self.order_flow.summary_recorder.record_match_only_skip = Mock()
```

#### التحقق
```bash
py -m unittest tests.test_tawreed_api_execution_mode.TawreedApiExecutionModeTests.test_api_match_only_flow_reuses_one_client_for_all_items -v
```

---

### 2.2 إصلاح Playwright Page Mocking

**الأولوية:** 🟡 **متوسطة**  
**التأثير:** 5 اختبارات فاشلة  
**الوقت المقدّر:** 1-2 ساعات

#### المشكلة
```python
# الاختبارات:
test_direct_dom_match_records_discount_and_store_name
test_matched_product_row_does_not_research_active_winning_query  
test_max_discount_add_records_best_store_metadata
test_multi_store_add_records_split_discount_and_store_name

# الخطأ المشترك:
AttributeError: 'object' object has no attribute 'locator'
AttributeError: 'object' object has no attribute 'expect_response'
```

#### السبب
```python
# الكود الحالي في tests/test_tawreed_products_flow.py
row = matched_product_row(bot, object(), match, ...)
                              ^^^^^^^
# استخدام object() بدلاً من Playwright page mock صحيح
```

#### الحل
```python
# في tests/test_tawreed_products_flow.py

from unittest.mock import Mock, MagicMock

def _mock_playwright_page():
    """Create a proper Playwright page mock."""
    page = Mock()
    
    # Mock locator
    locator_mock = Mock()
    locator_mock.count.return_value = 1
    locator_mock.first = Mock()
    locator_mock.all.return_value = []
    page.locator.return_value = locator_mock
    
    # Mock expect_response
    response_mock = Mock()
    response_mock.json.return_value = {}
    context_manager = MagicMock()
    context_manager.__enter__.return_value = response_mock
    context_manager.__exit__.return_value = None
    page.expect_response.return_value = context_manager
    
    # Mock wait_for_selector
    page.wait_for_selector.return_value = Mock()
    
    return page

# استخدام:
def test_direct_dom_match_records_discount_and_store_name(self):
    page = _mock_playwright_page()  # ✅ بدلاً من object()
    row = matched_product_row(bot, page, match, ...)
```

#### التحقق
```bash
py -m unittest tests.test_tawreed_products_flow.TawreedProductsFlowTests -v
```

---

### 2.3 إصلاح Cart Removal Arabic Name

**الأولوية:** 🟡 **متوسطة**  
**التأثير:** 1 اختبار فاشل  
**الوقت المقدّر:** 30 دقيقة

#### المشكلة
```python
# الاختبار:
test_resolve_cart_removal_targets_adds_tawreed_arabic_name

# الخطأ:
AssertionError: 'ديفارول اس 200000 وحده 1 امبول' not found in ['DEVAROL-S-200.000 I.U 1 AMP']

# خطأ إضافي في stdout:
Could not resolve name for DEVAROL-S-200.000 I.U 1 AMP: 'Bot' object has no attribute 'log'
```

#### السبب المزدوج
1. الاسم العربي لا يُضاف بشكل صحيح
2. Bot mock لا يحتوي على `log` method

#### الحل
```python
# في tests/test_tawreed_cart_removal.py

def _mock_bot():
    bot = Mock()
    bot.log = Mock()  # ✅ أضف log method
    bot.skip_item_exception = _SkipException
    # ... rest of mock setup
    return bot

# وفي الكود الأصلي (إذا كان الخطأ هناك):
# src/tawreed/tawreed_cart_removal_helpers.py
def resolve_cart_removal_targets(bot, page, items):
    for item in items:
        try:
            match = require_product_match(bot, page, item, False)
            # ✅ تأكد من إضافة الاسم العربي
            names = [match.product_name_en]
            if hasattr(match, 'product_name_ar') and match.product_name_ar:
                names.append(match.product_name_ar)
            target = CartRemovalTarget(item.code, names)
            # ...
        except Exception as e:
            # ✅ حماية log
            if hasattr(bot, 'log'):
                bot.log(f"Could not resolve: {e}")
```

#### التحقق
```bash
py -m unittest tests.test_tawreed_cart_removal.TawreedCartRemovalTests.test_resolve_cart_removal_targets_adds_tawreed_arabic_name -v
```

---

## 🟢 المستوى 3: تحسينات اختيارية

### 3.1 إصلاح Test File Fixtures

**الأولوية:** 🟢 **منخفضة**  
**التأثير:** 2 اختبارات فاشلة (بسبب ملف مفقود)  
**الوقت المقدّر:** 1 ساعة

#### المشكلة
```python
# الاختبارات:
test_load_order_items_filters_prevented_items
test_load_order_items_ignores_missing_prevented_items_file

# الخطأ:
FileNotFoundError: [Errno 2] No such file or directory: 'data\\input\\order_items\\orders.xlsx'
```

#### الحل - الخيار 1: إنشاء Fixture
```python
# في tests/test_cli_commands.py

import tempfile
from openpyxl import Workbook

def _create_test_excel():
    """Create a temporary test Excel file."""
    wb = Workbook()
    ws = wb.active
    ws.append(["كود", "إسم الصنف", "الكمية"])
    ws.append(["1", "PANADOL", "5"])
    ws.append(["2", "ASPIRIN", "10"])
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    wb.save(temp_file.name)
    return temp_file.name

# استخدام:
def test_load_order_items_filters_prevented_items(self):
    test_file = _create_test_excel()
    try:
        args = Namespace(excel=test_file, limit=0)
        # ... rest of test
    finally:
        os.unlink(test_file)
```

#### الحل - الخيار 2: Mock Load Function
```python
# في tests/test_cli_commands.py

@patch('src.core.utils.excel_readers.load_items_from_excel')
def test_load_order_items_filters_prevented_items(self, mock_load):
    mock_load.return_value = iter([
        Item("1", "PANADOL", 5),
        Item("2", "ASPIRIN", 10),
    ])
    # ... rest of test
```

---

### 3.2 المرحلة C: مزامنة rule_audit.py

**الأولوية:** 🟢 **منخفضة** (بعد حل كل الاختبارات)  
**الوقت المقدّر:** 2-3 ساعات

#### الهدف
```bash
py tools/rule_audit.py
# يجب أن يطبع: rule_audit_ok
# ويرجع: exit code 0
```

#### الخطوات
```bash
# 1. تنفيذ الأداة وحفظ المخالفات الحالية
py tools/rule_audit.py > /tmp/violations.txt 2>&1

# 2. تحليل المخالفات
grep ":" /tmp/violations.txt | grep -v "rule_audit" > /tmp/clean_violations.txt

# 3. تصنيف المخالفات
# - docstring: أصلح فوراً (أضف docstring بسيط)
# - line_length: أصلح إذا كان سهلاً (كسر سطر)
# - function_lines: أضف للـ baseline (يحتاج refactoring)
# - file_lines: أضف للـ baseline أو EXCEPTED_FILE_LENGTHS
```

#### التعديلات المطلوبة
```python
# في tools/rule_audit.py

BASELINE_VIOLATIONS = {
    # حذف المفاتيح القديمة (للملفات المقسّمة)
    # مثل: "ai_steps.py:file_lines:1037" ← لم يعد موجود
    
    # إضافة المخالفات الجديدة المقبولة مؤقتاً
    "normalizer_matching_core.py:function_lines:85": ...,
    "indexer_detailed_lookup.py:function_lines:120": ...,
    # ... etc
}

EXCEPTED_FILE_LENGTHS = {
    # حذف الملفات التي صارت < 100 سطر
    # الإبقاء فقط على الملفات الضخمة فعلياً
    "tawreed_order_processing.py": 159,
    "tawreed_api_discovery_enhanced.py": 156,
    # ... only files still > 100 lines
}
```

---

### 3.3 المرحلة D: تحديث التوثيق

**الأولوية:** 🟢 **منخفضة** (في النهاية)  
**الوقت المقدّر:** 1 ساعة

#### الملفات المطلوب تحديثها

##### 1. REFACTORING_PROGRESS_REPORT.md
```markdown
# تحديثات مطلوبة:

## النتائج النهائية:
- إجمالي الاختبارات: 429 ✅
- الاختبارات الناجحة: 429 ← [تحديث بعد إكمال الإصلاحات]
- نسبة النجاح: 100% ← [تحديث]

## المرحلة 5: P0.5 Stabilization (جديد)
- إصلاح 20 خطأ استيراد ✅
- إصلاح components_match ✅
- إصلاح merge logic ✅
- ...
```

##### 2. PROJECT_MAP.md
```markdown
# إضافة الوحدات الجديدة:

## Tawreed Module Extensions
- tawreed_api_exceptions.py (NEW)
- tawreed_products_flow_discount.py
- tawreed_products_flow_stores.py
- ...

## CLI Module Reorganization  
- cli_order_items_loading.py
- cli_order_items_filtering.py
- ...
```

##### 3. REFACTORING_DETAILED_PLAN.md
```markdown
# إضافة ملاحظة:

## P0.5 Stabilization (Completed)
تم تنفيذ التقسيم (P1) فعلياً لكنه تطلّب مرحلة تثبيت إضافية:
- 20 خطأ استيراد مُصلَح
- 3 circular imports محلول
- components_match مُستعاد
...
```

---

## 📊 جدول الأولويات الملخص

| # | المهمة | الأولوية | الوقت | الحالة |
|---|--------|----------|------|--------|
| 1 | إصلاح components_match | 🔴🔴🔴 | 2-3h | ⏳ **يجب فوراً** |
| 2 | إصلاح merge logic | 🔴 | 1h | ⏳ عاجل |
| 3 | Bot mocking (API tests) | 🟡 | 30m | ⏳ مستحسن |
| 4 | Playwright mocking | 🟡 | 1-2h | ⏳ مستحسن |
| 5 | Cart removal arabic | 🟡 | 30m | ⏳ مستحسن |
| 6 | Test fixtures | 🟢 | 1h | ⏸️ اختياري |
| 7 | rule_audit sync | 🟢 | 2-3h | ⏸️ بعد الاختبارات |
| 8 | Documentation | 🟢 | 1h | ⏸️ في النهاية |

**إجمالي الوقت للإكمال الكامل:** 9-12 ساعة

---

## ✅ معايير الإتمام

### المستوى 1 (الحرج)
```bash
# يجب أن يمر:
py -m unittest tests.test_drug_matching_normalizer -v
py -m unittest tests.test_cli_commands -v

# النتيجة المطلوبة:
Ran X tests in Y.YYs
OK (skipped=4)
```

### المستوى 2 (المتوسط)
```bash
py -m unittest discover -s tests -v

# النتيجة المطلوبة:
Ran 429 tests in XX.XXs
OK (skipped=4)
```

### المستوى 3 (الكامل)
```bash
py -m unittest discover -s tests -q && py tools/rule_audit.py

# النتيجة المطلوبة:
Ran 429 tests in XX.XXs
OK (skipped=4)
rule_audit_ok
```

---

## 📝 ملاحظات تنفيذية

### قبل البدء
```bash
# نقطة حفظ
git add -A
git commit -m "checkpoint: before remaining fixes"
```

### بعد كل إصلاح
```bash
# تشغيل الاختبار المحدد
py -m unittest tests.test_xxx -v

# إذا نجح:
git add -A
git commit -m "fix: description of fix"
```

### بعد الإكمال
```bash
# اختبار شامل
py -m unittest discover -s tests -q
py tools/rule_audit.py

# إذا كل شيء أخضر:
git add -A
git commit -m "feat(P0.5): complete stabilization phase"
git tag -a v0.5-stable -m "P0.5 Stabilization Complete"
```

---

*نهاية الخطة التفصيلية*
