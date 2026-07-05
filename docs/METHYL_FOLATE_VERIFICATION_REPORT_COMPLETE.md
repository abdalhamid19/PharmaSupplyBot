# تقرير التحقق من تنفيذ خطة METHYL FOLATE ORCHIDIA MISMATCH

> **تاريخ التقرير:** 2026-07-05  
> **نطاق التحقق:** فحص تنفيذ خطة `METHYL_FOLATE_ORCHIDIA_MISMATCH_ANALYSIS.md`  
> **الصنف المعني:** `83165 - METHYL FOLATE 30 CAP ORCHIDIA`  
> **المشكلة:** مطابقة خاطئة مع `METHYL FOLATE ORA 30 CAPS` بدلاً من المرشح الصحيح

---

## 📋 الملخص التنفيذي

تم تنفيذ **40% فقط** من الخطة المطلوبة. البنية التحتية (infrastructure) موجودة لكن **التطبيق الفعلي غير مكتمل**.

### ✅ ما تم إنجازه (3 من 7 مراحل):
- **M2**: إصلاح config وإضافة المفاتيح الجديدة - **مكتمل 100%**
- **M6**: تحسين artifacts وإضافة حقول توضيحية - **مكتمل 100%**
- **M5**: إنشاء دوال التحقق من السلامة - **مكتمل 60%** (موجودة لكن غير مفعلة)

### ❌ ما لم يتم إنجازه (4 من 7 مراحل):
- **M0**: إيقاف النزيف فوراً (حذف القرار المحفوظ الخاطئ) - **0%**
- **M1**: اختبارات فاشلة توثق المشكلة - **0%**
- **M3**: إصلاح parsing للـ manufacturer - **0%**
- **M4**: تنفيذ logic لرفض extra brand tokens - **0%**

### 🔴 النتيجة النهائية:
**المشكلة الأساسية لا تزال موجودة ولم يتم حلها.**

---

## 📚 هيكل التقرير

### الفصل 1: تحليل الملفات المعدلة
تفاصيل كل ملف تم تعديله ومدى مطابقته لمتطلبات الخطة.

### الفصل 2: مطابقة التنفيذ مع مراحل الخطة (M0-M6)
مقارنة تفصيلية بين ما كان مطلوباً وما تم تنفيذه فعلياً.

### الفصل 3: النقاط الحرجة غير المنفذة
تحليل المشاكل الخطيرة التي لم يتم معالجتها.

### الفصل 4: اختبار المشكلة الحالية
التحقق من أن المشكلة الأصلية لا تزال موجودة.

### الفصل 5: خطة الإصلاح الكاملة والمفصلة
قائمة مرتبة بالأولوية لجميع المهام المتبقية والإصلاحات المطلوبة.

---

## ⚠️ ملاحظة هامة قبل البدء

قبل قراءة هذا التقرير، يجب فهم أن:
- **البنية التحتية موجودة** (config fields, validation functions, artifact fields)
- **لكنها غير مستخدمة** (الميزات معطلة، validation معطل، logic غير موجود)
- **القرار المحفوظ الخاطئ لا يزال موجوداً** في `docs/saved_corrected_items(2).csv`
- **النظام سيستمر في قبول ORA** حتى يتم إكمال الإصلاحات المتبقية

---

_انتهت المقدمة والهيكل العام. جاهز لكتابة الفصول عند الطلب._


---

## الفصل 1: تحليل الملفات المعدلة (الجزء 1 من 3)

### 1. src/core/config/config_models.py

**الحالة:** ✅ تم التعديل جزئياً

**التعديلات المنفذة:**

```python
# السطر 62-64
enable_manufacturer_check: bool = False
manufacturer_match_threshold: float = 0.85
reject_extra_brand_token: bool = False
```

**التحليل:**
- ✅ تم إضافة الحقول الثلاثة المطلوبة إلى `MatchingConfig`
- ✅ الأسماء مطابقة تماماً لما في الخطة
- ⚠️ **مشكلة حرجة:** القيم الافتراضية كلها `False` مما يعني:
  - فحص الشركة معطل
  - رفض extra brand tokens معطل
  - حتى لو وُضعت القيم في `config.yaml`، الافتراضي يظل معطلاً

**المطابقة مع الخطة:**
- ✅ M2: إضافة `reject_extra_brand_token` إلى `MatchingConfig` - **مكتمل**
- ✅ M2: `enable_manufacturer_check` موجود من خطة سابقة - **مكتمل**
- ⚠️ M0: لم يتم تفعيل الميزات

**الكود الفعلي (تم فحصه):**
```python
python -c "from src.core.config.config_models import MatchingConfig; cfg = MatchingConfig(); print('reject_extra_brand_token:', cfg.reject_extra_brand_token)"
# Output: reject_extra_brand_token: False
```

**التوصية:**
- القيم الافتراضية صحيحة (False) للأمان
- لكن يجب تفعيلها في `state/config.yaml` بعد اكتمال التطبيق

---

### 2. src/core/config/config_factory.py

**الحالة:** ✅ تم التعديل كلياً

**التعديلات المنفذة:**

```python
# السطر 73-74 (في bool_keys)
"enable_manufacturer_check",
"reject_extra_brand_token",

# السطر 100 (في float keys)
"manufacturer_match_threshold",
```

**التحليل:**
- ✅ تم إضافة `enable_manufacturer_check` إلى `bool_keys`
- ✅ تم إضافة `reject_extra_brand_token` إلى `bool_keys`
- ✅ تم إضافة `manufacturer_match_threshold` إلى قائمة floats
- ✅ هذا يعني أن `build_matching_config` سيقرأ هذه المفاتيح من YAML

**المطابقة مع الخطة:**
- ✅ M2: "تعديل `config_factory.py` ليقرأ المفاتيح" - **مكتمل 100%**
- ✅ هذا يحل المشكلة رقم 2 من القسم 3 في الخطة الأصلية

**الاختبار:**
قمت بفحص أن المفاتيح موجودة في الكود:
```
grep -n "enable_manufacturer_check\|reject_extra_brand_token\|manufacturer_match_threshold" src/core/config/config_factory.py
# Output: Lines 73, 74, 100 ✓
```

**التوصية:**
- هذا الجزء مثالي ✓
- لا حاجة لأي تعديل

---

### 3. state/config.yaml

**الحالة:** ⚠️ تم التعديل جزئياً

**التعديلات المنفذة:**

```yaml
# السطر 84
reject_extra_brand_token: false
```

**التحليل:**
- ✅ يحتوي على `reject_extra_brand_token: false`
- ✅ تعليقات توضيحية ممتازة (السطور 77-83):
  ```yaml
  # Examples where rejection occurs when enabled:
  #   - Query "CAL MAG 30 TAB" → Candidate "CAL MAG JOINT 30 TAB" (JOINT is extra)
  #   - Query "LIMITLESS MILGA MAX" → Candidate "LIMITLESS MAN MAX" (MAN is extra)
  #   - Query "METHYL FOLATE ORCHIDIA" → Candidate "METHYL FOLATE ORA" (ORA is extra)
  ```
- ❌ **لا يحتوي على** `enable_manufacturer_check` صراحة
- ⚠️ القيمة `false` تعني الميزة معطلة

**ملاحظة مهمة:**
فحصت `config.example.yaml` ووجدت:
```yaml
enable_manufacturer_check: false
manufacturer_match_threshold: 0.85
reject_extra_brand_token: false
```

**المطابقة مع الخطة:**
- ✅ M2: "إضافة المفتاح إلى `state/config.yaml`" - **مكتمل جزئياً**
- ❌ M0: "تفعيل المفاتيح" - **لم يتم**

**التوصية:**
- إضافة `enable_manufacturer_check: true` عندما يكتمل M3
- تغيير `reject_extra_brand_token: true` عندما يكتمل M4
- حالياً القيم صحيحة (false) لأن التطبيق غير مكتمل


---

## الفصل 1: تحليل الملفات المعدلة (الجزء 2 من 3)

### 4. src/core/manual_review/manual_review_runtime.py

**الحالة:** ✅ تم التعديل كلياً

**التعديلات المنفذة:**

```python
# السطر 22
from .manual_review_helpers import (
    ...
    should_skip_auto_save,  # ✓ تم الاستيراد
)

# السطور 135-152
def should_skip_auto_save_verified_match(
    item: Item, candidate: dict, rejection_reason: str | None = None
) -> bool:
    """Wrapper for should_skip_auto_save with proper logging."""
    return should_skip_auto_save(item, candidate, rejection_reason)
```

**التحليل:**
- ✅ تم إنشاء wrapper function `should_skip_auto_save_verified_match`
- ✅ تم استيراد `should_skip_auto_save` من helpers
- ✅ الدالة موثقة بشكل صحيح
- ❌ **مشكلة حرجة:** الدالة **لم يتم استدعاؤها** في `_auto_save_verified_match`

**فحص الاستخدام:**
```bash
grep -r "should_skip_auto_save_verified_match" src/
# Output: فقط في manual_review_runtime.py - لا يوجد استدعاء!
```

**المطابقة مع الخطة:**
- ✅ M5: "إضافة safety validation" - **الدالة موجودة**
- ❌ M5: "تطبيقها في _auto_save_verified_match" - **لم يتم**

**التوصية:**
- يجب استدعاء هذه الدالة في `tawreed_order_summary_build.py:_auto_save_verified_match`

---

### 5. src/core/manual_review/manual_review_helpers.py

**الحالة:** ✅ تم التعديل كلياً (250+ سطر جديد)

**التعديلات المنفذة:**

**أ) دوال التحقق من السلامة:**
```python
# _validate_manual_review_match (35 سطر)
# _validate_product_id_match (19 سطر)
# _validate_manufacturer_match (20 سطر)
# _validate_name_consistency (24 سطر)
# _extract_item_manufacturer (9 أسطر)
# _extract_candidate_manufacturer (15 سطر)
# _is_major_name_change (22 سطر)
# should_skip_auto_save (37 سطر)
```

**ب) تحديث دوال manual review:**
```python
def _manual_review_id_match(...):
    # السطر 216-219
    # validation = _validate_manual_review_match(...)
    # if not validation["valid"]:
    #     return None  # Skip validation for ID match
```

**التحليل:**
- ✅ تم إنشاء 8 دوال validation شاملة وموثقة
- ✅ الكود منظم ومنطقي
- ✅ التعليقات واضحة
- ⚠️ **مشكلة حرجة:** الـ validation **معطل** في `_manual_review_id_match` و `_manual_review_name_match`
- ⚠️ التعليق يقول صراحة: "Skip validation for ID match to preserve backward compatibility"

**الكود الفعلي:**
```python
# السطر 216-219 (معلق!)
# validation = _validate_manual_review_match(item, decision, candidate)
# if not validation["valid"]:
#     return None
```

**المطابقة مع الخطة:**
- ✅ M5: "إضافة safety validation قبل forced manual review match" - **الكود موجود**
- ❌ M5: "تطبيقه فعلياً" - **معطل للتوافق الخلفي**

**الخطورة:**
هذا يعني أن القرار المحفوظ الخاطئ (الصنف 83165 → ORA) سيستمر في العمل بدون أي فحص!

**التوصية:**
- إزالة التعليق وتفعيل validation على الأقل لـ `auto_matched` decisions
- الإبقاء على validation معطل فقط لـ `approved_match` (القرارات البشرية)

---

### 6. src/tawreed/api/tawreed_api_matching.py

**الحالة:** ❌ لم يتم التعديل

**الوضع الحالي:**
- الكود يستدعي `manual_review_match` ثم `explain_best_product_match`
- لا توجد أي طبقة validation إضافية
- القرارات المحفوظة تحصل على score 999 بدون فحص

**التحليل:**
- ❌ لم يتم إضافة أي تعديلات
- ❌ لا يوجد استدعاء لـ validation functions
- ❌ المسار القديم لا يزال يعمل بدون تغيير

**المطابقة مع الخطة:**
- ❌ لم يتم ذكر تعديلات مطلوبة صراحة في الخطة لهذا الملف
- لكن المنطق يقول: يجب أن يكون هناك safety check قبل قبول score 999

**التوصية:**
- إضافة check في `_api_match_decision` قبل إرجاع manual review match
- على الأقل log warning إذا كان القرار `auto_matched` ولديه manufacturer conflict

---

### 7. src/core/matching/product_matching_acceptance.py

**الحالة:** ✅ موجود من خطة سابقة

**التعديلات الموجودة (من خطة MANUFACTURER_MISMATCH_FIX_PLAN.md السابقة):**

```python
# السطور 318-349
def _candidate_manufacturer_rejection(
    query: str,
    candidate: dict[str, Any],
    config: dict[str, Any] | MatchingConfig,
) -> tuple[bool, str | None]:
    """Check for manufacturer conflict."""
    enable_check = (
        config.enable_manufacturer_check
        if hasattr(config, "enable_manufacturer_check")
        else config.get("enable_manufacturer_check", False)
    )
    if not enable_check:
        return True, None  # ← الفحص معطل افتراضياً
    
    # استخراج الشركات ومقارنتها...
```

**الكود في `_check_rejections` (السطور 354-385):**
```python
def _check_rejections(...):
    # السطور 370-380
    enable_check = config.enable_manufacturer_check if ... else False
    if enable_check:
        is_ok, reason = _candidate_manufacturer_rejection(...)
        if not is_ok:
            return True, reason or "Manufacturer conflict"
```

**التحليل:**
- ✅ الكود موجود ويعمل
- ✅ يتم استدعاء `extract_manufacturer_from_name` و `manufacturer_conflict`
- ⚠️ **معطل افتراضياً** لأن `enable_manufacturer_check = False`
- ✅ عند التفعيل، سيرفض ORCHIDIA vs ORA

**الاختبار:**
```python
# من الخطة الأصلية:
# مع enable_manufacturer_check=False → يقبل ORA
# مع enable_manufacturer_check=True → يرفض ORA بـ "Manufacturer conflict: ORCHIDIA vs ORA"
```

**المطابقة مع الخطة:**
- ✅ الكود جاهز
- ❌ لم يتم تفعيله في config

**التوصية:**
- تفعيله بعد إكمال M3 (إصلاح parsing)


---

## الفصل 1: تحليل الملفات المعدلة (الجزء 3 من 3)

### 8. src/core/identity/manufacturer_identity.py

**الحالة:** ✅ موجود من خطة سابقة (لم يتم تعديله في هذه الخطة)

**الوضع الحالي:**
```python
def extract_manufacturer_from_name(item_name: str) -> str | None:
    """استخراج الشركة من اسم الصنف - يأخذ آخر token غير عام"""
    # يستخرج آخر كلمة من اسم الصنف
    # مثال: "METHYL FOLATE 30 CAP ORCHIDIA" → "ORCHIDIA"

def extract_manufacturer_from_candidate(
    candidate_name: str, 
    company_name: str | None, 
    supplier_name: str | None
) -> str | None:
    """استخراج الشركة من المرشح - من companyName أو اسم المنتج"""

def manufacturer_conflict(
    query_company: str | None,
    candidate_company: str | None,
    threshold: float = 0.85
) -> bool:
    """فحص التعارض بين الشركات"""
```

**التحليل:**
- ✅ الكود موجود ويعمل من خطة سابقة
- ⚠️ **مشكلة محتملة:** كما ذكرت الخطة الأصلية:
  - "استخراج الشركة من اسم الصنف يعتمد على آخر token"
  - "هذا صحيح صدفة في ORCHIDIA، لكنه خطر في أسماء كثيرة"
- ⚠️ `companyName` في Tawreed غالباً مخزن/مورد وليس manufacturer

**أمثلة المشاكل المحتملة:**
```
"VITAMIN C 500 TABLETS" → يعتبر "TABLETS" شركة!
"ASPIRIN 100 MG COATED" → يعتبر "COATED" شركة!
```

**المطابقة مع الخطة:**
- ✅ الكود موجود
- ❌ M3: لم يتم تحسين الاستخراج ليكون أكثر أماناً
- ⚠️ الخطة تقول: "يحتاج known manufacturer list" أو "استخراج من الأقواس"

**التوصية:**
- حالياً: الكود يعمل للحالة البسيطة (ORCHIDIA في النهاية)
- مستقبلاً: يجب تحسينه بـ:
  - قائمة شركات معروفة
  - استخراج من الأقواس `(ORCHIDIA)`
  - استثناء الكلمات العامة (TABLETS, COATED, etc.)

---

### 9. src/core/drug_matching/normalization/normalizer_matching_brand.py

**الحالة:** ❌ لم يتم التعديل

**الوضع الحالي:**
- لا يزال يرفض `METHYL FOLATE (ORCHIDIA) 30 CAPS` مقابل `METHYL FOLATE 30 CAP ORCHIDIA`
- السبب: parsing يجعل brand مختلف:
  - Query: `METHYL FOLATE 30 CAP ORCHIDIA` → brand = `METHYLFOLATE`
  - Candidate: `METHYL FOLATE (ORCHIDIA) 30 CAPS` → brand = `METHYLFOLATEORCHIDIA`
- `_brand_match_check` يعتبرهما `different_brand`

**التحليل:**
- ❌ **المشكلة الأساسية لم تُحل**
- ❌ المرشح الصحيح لا يزال يُرفض
- ❌ هذا هو السبب الرئيسي في القسم 2.3 من الخطة

**من الأدلة الأصلية:**
```
| rank | accepted | product | score | reason |
|---|---:|---|---:|---|
| 1 | False | METHYL FOLATE (ORCHIDIA) 30 CAPS | 21.128814 | Semantic token conflict: different_brand |
| 7 | True | METHYL FOLATE ORA 30 CAPS | 19.103704 | accepted |
```

**المطابقة مع الخطة:**
- ❌ M3: "تعديل parsing أو component matching" - **لم يتم**
- ❌ M3: "لا يعتبر (ORCHIDIA) جزءاً من brand الأساسي" - **لم يتم**
- ❌ M3: "جعل المرشحين متوافقين" - **لم يتم**

**الخطورة:**
هذه هي **المشكلة الأساسية**. حتى لو فعّلنا manufacturer check، المرشح الصحيح سيُرفض قبل أن نصل لفحص الشركة!

**التوصية:**
- **أولوية حرجة**: يجب إصلاح parsing ليتعرف على:
  - كلمات داخل أقواس `(ORCHIDIA)` كـ manufacturer/descriptor
  - آخر token قبل الأرقام كـ manufacturer محتمل
  - التمييز بين brand و manufacturer

---

### 10. tests/test_manufacturer_mismatch.py

**الحالة:** ⚠️ تم التعديل جزئياً

**التعديلات المنفذة:**
```python
# السطور 138-150
class FailingTestsForBugDocumentation:
    """Tests that document the current failing behavior."""
    # تم إضافة class فارغ للتوثيق
```

**الاختبارات الموجودة:**
```python
# 5 اختبارات تمر بنجاح:
test_orchidia_vs_ora_explicit_company_names  # ✓ PASSED
test_orchidia_vs_ora_produces_conflict_or_unsafe_match  # ✓ PASSED
test_same_company_different_spelling_no_conflict  # ✓ PASSED
test_missing_company_on_query_side_no_conflict  # ✓ PASSED
test_missing_company_on_candidate_side_no_conflict  # ✓ PASSED
```

**التحليل:**
- ✅ الاختبارات الموجودة تمر
- ⚠️ **لكنها تختبر `enable_manufacturer_check=True` يدوياً**
- ❌ لا تختبر السلوك الافتراضي (config من YAML)
- ❌ لا تختبر manual review saved matches
- ❌ لا تختبر auto-save behavior
- ❌ لا توجد اختبارات فاشلة كما طلبت M1

**المطابقة مع الخطة:**
- ❌ M1: "اختبارات فاشلة أولاً" - **لم يتم**
- ⚠️ M2: "اختبار أن config YAML يُقرأ صحيحاً" - **غير موجود**
- ❌ M5: "اختبار saved match validation" - **غير موجود**

**ما كان يجب أن يُكتب (حسب M1):**
```python
def test_default_config_rejects_ora_for_orchidia():
    # يجب أن يفشل حالياً
    config = build_matching_config_from_yaml()  # ← يقرأ من YAML
    result = explain_best_product_match(...)
    # يجب أن يرفض ORA أو يرسله للمراجعة اليدوية

def test_saved_auto_matched_ora_fails_validation():
    # يجب أن يفشل حالياً
    decision = ManualReviewDecision(decision_type="auto_matched", ...)
    should_skip = should_skip_auto_save(item, ora_candidate)
    assert should_skip == True  # ← يجب أن يرفض حفظه
```

**التوصية:**
- إضافة اختبارات تفشل حالياً وتنجح بعد الإصلاح
- اختبار السلوك الكامل (config + manual review + auto-save)

---

## ملخص الفصل 1

| الملف | الحالة | نسبة الإنجاز | الملاحظات الحرجة |
|---|---|---:|---|
| config_models.py | ✅ مكتمل | 100% | القيم الافتراضية False (صحيح للأمان) |
| config_factory.py | ✅ مكتمل | 100% | يقرأ المفاتيح بشكل صحيح |
| config.yaml | ⚠️ جزئي | 60% | المفاتيح موجودة لكن معطلة |
| manual_review_runtime.py | ⚠️ جزئي | 70% | الدالة موجودة لكن غير مستخدمة |
| manual_review_helpers.py | ⚠️ جزئي | 60% | 250+ سطر لكن validation معطل |
| tawreed_api_matching.py | ❌ لم يتم | 0% | لا توجد تعديلات |
| product_matching_acceptance.py | ✅ موجود | 100% | من خطة سابقة، معطل |
| manufacturer_identity.py | ✅ موجود | 100% | من خطة سابقة، يحتاج تحسين |
| normalizer_matching_brand.py | ❌ لم يتم | 0% | **المشكلة الأساسية هنا** |
| test_manufacturer_mismatch.py | ⚠️ جزئي | 30% | لا توجد اختبارات فاشلة |

**الخلاصة:** البنية التحتية موجودة (40%)، لكن التطبيق الفعلي ناقص (60%).


---

## الفصل 2: مطابقة التنفيذ مع مراحل الخطة (M0-M6)

### ❌ M0 - إيقاف النزيف فوراً

**المطلوب حسب الخطة:**
1. استخراج قرار manual review للصنف 83165 من قاعدة البيانات
2. حذف أو تحويل القرار إلى `not_matching`
3. تعطيل auto-save مؤقتاً للصنف
4. تشغيل match-only للتأكد من عدم استخدام score 999

**ما تم تنفيذه:**
- ❌ لم يتم حذف القرار من قاعدة البيانات
- ❌ لم يتم تعطيل auto-save
- ❌ لم يتم تشغيل match-only للتحقق

**الدليل:**
```csv
# docs/saved_corrected_items(2).csv - السطر 614
83165,METHYL FOLATE 30 CAP ORCHIDIA,auto_matched,METHYL FOLATE ORA 30 CAPS,ميثيل فولات اورا 30 كبسول
```

القرار الخاطئ **لا يزال موجوداً** في ملف CSV.

**معيار النجاح (من الخطة):**
- ❌ لا يظهر `Approved by saved manual review` للصنف 83165
- ❌ لا يتم add-to-cart لـ ORA

**نسبة الإنجاز: 0%**

**الخطورة:** 🔴 حرجة - القرار المحفوظ سيستمر في فرض ORA بدرجة 999

---

### ❌ M1 - اختبارات فاشلة أولاً

**المطلوب حسب الخطة:**
إضافة اختبارات تثبت الفشل الحالي:
1. default config لا يجب أن يقبل ORA لـ ORCHIDIA
2. المرشح الصحيح `(ORCHIDIA)` يجب أن يفوز على ORA
3. `reject_extra_brand_token` من YAML يجب أن يصل إلى MatchingConfig
4. saved `auto_matched` خاطئ يجب أن يفشل validation
5. auto-save لا يحفظ ORA عندما الطلب يحتوي ORCHIDIA

**ما تم تنفيذه:**
```python
# tests/test_manufacturer_mismatch.py - السطور 138-150
class FailingTestsForBugDocumentation:
    """Tests that document the current failing behavior."""
    # Class فارغ للتوثيق فقط
```

- ❌ لا توجد اختبارات فاشلة فعلية
- ✅ الاختبارات الموجودة (5 اختبارات) تمر بنجاح
- ⚠️ لكنها تختبر `enable_manufacturer_check=True` يدوياً، وليس السلوك الافتراضي

**معيار النجاح (من الخطة):**
- ❌ الاختبارات تفشل قبل الإصلاح
- ❌ الاختبارات تنجح بعد الإصلاح

**نسبة الإنجاز: 10%** (فقط توثيق)

**الخطورة:** 🟡 متوسطة - بدون اختبارات فاشلة، لا نضمن أن الإصلاح يحل المشكلة

---

### ✅ M2 - إصلاح config

**المطلوب حسب الخطة:**
1. إضافة `reject_extra_brand_token` إلى `MatchingConfig`
2. إضافة `enable_manufacturer_check` و`manufacturer_match_threshold` إلى `config_factory.py`
3. تحديث `config.example.yaml`
4. اختبار أن `config.yaml` ينتج config صحيح

**ما تم تنفيذه:**
- ✅ `config_models.py`: إضافة `reject_extra_brand_token: bool = False`
- ✅ `config_factory.py`: إضافة المفاتيح الثلاثة إلى `bool_keys` و float keys
- ✅ `config.example.yaml`: يحتوي على جميع المفاتيح
- ⚠️ `state/config.yaml`: يحتوي على `reject_extra_brand_token: false` فقط

**معيار النجاح (من الخطة):**
- ✅ لا توجد مفاتيح matching في YAML بلا تأثير

**نسبة الإنجاز: 100%**

**ملاحظة:** القيم `false` صحيحة حالياً لأن التطبيق غير مكتمل.

---

### ❌ M3 - إصلاح ORCHIDIA كـ manufacturer وليس brand

**المطلوب حسب الخطة:**
1. تعديل parsing بحيث لا يعتبر `(ORCHIDIA)` جزءاً من brand الأساسي
2. إضافة known manufacturer extraction من:
   - أقواس الاسم الإنجليزي
   - tail token معروف
   - قائمة شركات مضبوطة
3. اختبار أن `METHYL FOLATE 30 CAP ORCHIDIA` يطابق `METHYL FOLATE (ORCHIDIA) 30 CAPS`

**ما تم تنفيذه:**
- ❌ لم يتم تعديل `normalizer_matching_brand.py`
- ❌ لم يتم تعديل parsing logic
- ❌ المشكلة الأساسية لا تزال موجودة:
  ```
  Query: METHYL FOLATE 30 CAP ORCHIDIA → brand = METHYLFOLATE
  Candidate: METHYL FOLATE (ORCHIDIA) 30 CAPS → brand = METHYLFOLATEORCHIDIA
  Result: different_brand ✗
  ```

**معيار النجاح (من الخطة):**
- ❌ المرشح الصحيح ORCHIDIA accepted
- ❌ ORA rejected أو manual review

**نسبة الإنجاز: 0%**

**الخطورة:** 🔴 حرجة جداً - هذه المشكلة الأساسية التي تسبب رفض المرشح الصحيح

---

### ❌ M4 - تنفيذ extra brand token rejection

**المطلوب حسب الخطة:**
1. تطبيق `reject_extra_brand_token` في طبقة matching
2. استثناء generic/form/unit/numeric tokens
3. اختبار حالات مثل:
   - `CAL MAG 30TAB` لا يقبل `CAL MAG JOINT 30 TAB`
   - `LIMITLESS MILGA MAX` لا يقبل `LIMITLESS MAN MAX`

**ما تم تنفيذه:**
- ✅ المفتاح موجود في `MatchingConfig`
- ✅ يُقرأ من `config.yaml`
- ❌ **لا يوجد كود يستخدمه**

**فحص الكود:**
```bash
grep -r "reject_extra_brand_token" src/core/matching/
# Output: لا توجد نتائج!
```

لا يوجد أي استخدام للمفتاح في:
- `matching_penalties.py`
- `product_matching_acceptance.py`
- `_check_rejections`

**معيار النجاح (من الخطة):**
- ❌ تقليل false positives بدون كسر safe omissions

**نسبة الإنجاز: 20%** (المفتاح موجود فقط، logic غير موجود)

**الخطورة:** 🔴 حرجة - بدون هذا، ORA سيستمر في القبول كـ "extra token"


---

## الفصل 2: مطابقة التنفيذ مع مراحل الخطة (M5-M6) + الملخص

### ⚠️ M5 - حماية manual review والـ auto-save

**المطلوب حسب الخطة:**
1. إضافة safety validation قبل forced manual review match
2. إذا القرار `auto_matched` وفشل validation، يعاد إلى manual review
3. إذا القرار `approved_match` وفشل validation، يرفع تحذير
4. تعديل `_auto_save_verified_match` حتى لا يحفظ matches عليها conflict

**ما تم تنفيذه:**

#### الجزء 1: دوال التحقق (✅ موجودة)
```python
# manual_review_helpers.py
_validate_manual_review_match()      # 35 سطر ✓
_validate_product_id_match()         # 19 سطر ✓
_validate_manufacturer_match()       # 20 سطر ✓
_validate_name_consistency()         # 24 سطر ✓
should_skip_auto_save()              # 37 سطر ✓

# manual_review_runtime.py
should_skip_auto_save_verified_match()  # wrapper function ✓
```

#### الجزء 2: التطبيق (❌ غير مكتمل)

**أ) Validation في manual review matches:**
```python
# manual_review_helpers.py - السطور 216-219
def _manual_review_id_match(...):
    # validation = _validate_manual_review_match(item, decision, candidate)
    # if not validation["valid"]:
    #     return None
    # ↑ معلّق! "Skip validation for ID match to preserve backward compatibility"
```

**النتيجة:** القرارات المحفوظة (بما فيها الصنف 83165 → ORA) تُقبل بدون فحص!

**ب) Validation في auto-save:**
```python
# tawreed_order_summary_build.py - السطور 61-74
def _auto_save_verified_match(item: Item, decision) -> None:
    if not decision or not decision.best_match:
        return
    # لا يوجد استدعاء لـ should_skip_auto_save_verified_match!
```

**النتيجة:** auto-save يحفظ أي match بدون فحص conflict!

**معيار النجاح (من الخطة):**
- ❌ لا يستطيع قرار ORA محفوظ أن يتجاوز القواعد
- ❌ لا يعاد حفظ ORA تلقائياً

**نسبة الإنجاز: 60%** (الدوال موجودة لكن غير مطبقة)

**الخطورة:** 🔴 حرجة - المشكلة ستتكرر حتى لو حذفنا القرار الحالي

---

### ✅ M6 - artifacts ووضوح السبب

**المطلوب حسب الخطة:**
1. ملء `candidate_manufacturer` بصورة مفيدة
2. إضافة حقول جديدة في artifacts
3. جعل manual review يظهر عند manufacturer-mismatch

**ما تم تنفيذه:**

تم فحص `src/tawreed/order/order_run_artifact_rows.py` ووجدت:

```python
# حقول جديدة تم إضافتها:
saved_manual_review_decision: str | None
saved_manual_review_safety_decision: str | None
higher_scoring_rejected_candidate: str | None
higher_scoring_rejection_reason: str | None
```

**التحليل:**
- ✅ تم إضافة حقول artifact المطلوبة
- ✅ تحسين وضوح التقارير
- ✅ يمكن تتبع سبب رفض مرشحين أفضل

**معيار النجاح (من الخطة):**
- ✅ عند التدقيق، يظهر لماذا لم يضف النظام الصنف

**نسبة الإنجاز: 100%**

---

## جدول ملخص المراحل

| المرحلة | الوصف | نسبة الإنجاز | الحالة |
|---|---|---:|---|
| **M0** | إيقاف النزيف (حذف القرار الخاطئ) | 0% | ❌ لم يتم |
| **M1** | اختبارات فاشلة توثق المشكلة | 10% | ❌ لم يتم |
| **M2** | إصلاح config وقراءة المفاتيح | 100% | ✅ مكتمل |
| **M3** | إصلاح parsing للـ manufacturer | 0% | ❌ لم يتم |
| **M4** | تنفيذ reject_extra_brand_token | 20% | ❌ لم يتم |
| **M5** | حماية manual review وauto-save | 60% | ⚠️ جزئي |
| **M6** | تحسين artifacts والوضوح | 100% | ✅ مكتمل |
| **الإجمالي** | | **41%** | ⚠️ غير مكتمل |

---

## تحليل المسارات (من الخطة الأصلية)

### المسار 1: القرار المحفوظ (Score 999)

**الخطة قالت:**
> "عند وجود قرار محفوظ، الكود يطبقه قبل خوارزمية المطابقة ويمنحه score = 999.0"

**الوضع الحالي:**
- ❌ القرار المحفوظ (83165 → ORA) موجود في `docs/saved_corrected_items(2).csv`
- ❌ validation معطل في `_manual_review_id_match`
- ❌ النظام سيستمر في إعطاء ORA درجة 999

**النتيجة:** المسار 1 **لم يُغلق**.

---

### المسار 2: المطابقة الحتمية

**الخطة قالت:**
> "عند عدم استخدام القرار المحفوظ، الخوارزمية نفسها تقبل ORA بدرجة 19.103704"

**الوضع الحالي:**
- ❌ M3 لم يتم (المرشح الصحيح يُرفض بـ `different_brand`)
- ❌ M4 لم يتم (لا يوجد logic لرفض extra brand token)
- ⚠️ فحص الشركة موجود لكن معطل (`enable_manufacturer_check=False`)

**النتيجة:** المسار 2 **لم يُغلق**.

---

## القرار النهائي المقترح (من الخطة الأصلية)

**الخطة قالت:**
> "الأولوية العملية:
> 1. حذف قرار ORA المحفوظ للصنف 83165 فوراً
> 2. إصلاح رفض المرشح الصحيح ORCHIDIA
> 3. تنفيذ قراءة وتطبيق reject_extra_brand_token
> 4. حماية manual review وauto-save
> 5. تفعيل manufacturer check بصورة آمنة"

**ما تم تنفيذه من القائمة:**
- ❌ لم يتم حذف قرار ORA (الأولوية 1)
- ❌ لم يتم إصلاح رفض ORCHIDIA (الأولوية 2)
- ❌ لم يتم تطبيق reject_extra_brand_token (الأولوية 3)
- ⚠️ تم إنشاء دوال الحماية لكن لم تُطبق (الأولوية 4)
- ⚠️ manufacturer check موجود لكن معطل (الأولوية 5)

**الخلاصة:** لم يتم تنفيذ **أي من الأولويات الأربع الأولى** بشكل كامل.


---

## الفصل 3: النقاط الحرجة غير المنفذة

### 🔴 النقطة 1: القرار المحفوظ الخاطئ لا يزال موجود

**الموقع:**
```
docs/saved_corrected_items(2).csv - السطر 614
```

**المحتوى:**
```csv
83165,METHYL FOLATE 30 CAP ORCHIDIA,auto_matched,METHYL FOLATE ORA 30 CAPS,ميثيل فولات اورا 30 كبسول
```

**التحليل:**
- القرار من نوع `auto_matched` (ليس قراراً بشرياً)
- يربط الصنف 83165 بـ ORA بدلاً من ORCHIDIA الصحيح
- عند التشغيل التالي، سيحصل ORA على **score = 999.0**
- سيتجاوز جميع قواعد الأمان

**المسار الذي سيحدث:**
```python
1. manual_review_match() يبحث عن قرار محفوظ
2. يجد الصنف 83165 في القرارات المحفوظة
3. _manual_review_id_match() أو _manual_review_name_match()
4. validation معطل! (السطور 216-219 معلقة)
5. يرجع MatchDecision(score=999.0, reason="Approved by saved manual review")
6. add-to-cart لـ ORA ✗
```

**الخطورة:** 🔴🔴🔴 حرجة للغاية
- المشكلة ستحدث في **كل تشغيل**
- لن تظهر في manual review
- لن يتم اكتشافها إلا بالمراجعة اليدوية للنتائج

**الحل المطلوب فوراً:**
1. حذف السطر 614 من `docs/saved_corrected_items(2).csv`
2. أو تغيير `decision_type` إلى `not_matching`
3. أو حذف الصنف 83165 تماماً من الملف

---

### 🔴 النقطة 2: should_skip_auto_save غير مطبق

**الملف:** `src/tawreed/order/tawreed_order_summary_build.py`

**الكود الحالي:**
```python
# السطور 61-74
def _auto_save_verified_match(item: Item, decision) -> None:
    if not decision or not decision.best_match:
        return
    
    match = decision.best_match
    if match.score == 999.0 and "Approved by saved manual review" in ...:
        return  # لا تحفظ القرارات المحفوظة مسبقاً
    
    # ... بقية الكود
    # لا يوجد استدعاء لـ should_skip_auto_save_verified_match!
```

**المشكلة:**
- دالة `should_skip_auto_save_verified_match` موجودة في `manual_review_runtime.py`
- لكن **لم يتم استدعاؤها** في `_auto_save_verified_match`
- النظام سيحفظ matches خاطئة تلقائياً

**سيناريو الخطر:**
```
1. النظام يقبل ORA بدرجة 19.1 (بدون القرار المحفوظ)
2. auto-save يحفظه كـ auto_matched
3. في التشغيل التالي، يصبح قراراً محفوظاً بدرجة 999
4. المشكلة تتكرر!
```

**الحل المطلوب:**
```python
def _auto_save_verified_match(item: Item, decision) -> None:
    if not decision or not decision.best_match:
        return
    
    match = decision.best_match
    
    # ✓ إضافة هذا الفحص
    if should_skip_auto_save_verified_match(item, match.data):
        return
    
    # ... بقية الكود
```

**الخطورة:** 🔴🔴 حرجة
- المشكلة ستعيد إنتاج نفسها
- حذف القرار الخاطئ لن يكون كافياً

---

### 🔴 النقطة 3: validation معطل في manual review matches

**الملف:** `src/core/manual_review/manual_review_helpers.py`

**الكود الحالي:**
```python
# السطور 216-219
def _manual_review_id_match(...):
    # validation = _validate_manual_review_match(item, decision, candidate)
    # if not validation["valid"]:
    #     return None
    # ↑ معلّق! "Skip validation for backward compatibility"
```

**المشكلة:**
- تم إنشاء 8 دوال validation شاملة (250+ سطر)
- لكنها **معطلة** في الأماكن الحرجة
- السبب المذكور: "backward compatibility"

**التحليل:**
- القرارات البشرية (`approved_match`) يمكن السماح لها بتجاوز validation
- لكن القرارات التلقائية (`auto_matched`) **يجب** أن تخضع للفحص
- حالياً: كلاهما يتجاوز الفحص!

**الحل المطلوب:**
```python
def _manual_review_id_match(...):
    validation = _validate_manual_review_match(item, decision, candidate)
    
    # إذا كان auto_matched ولم ينجح validation، ارفضه
    if decision.decision_type == "auto_matched" and not validation["valid"]:
        return None
    
    # إذا كان approved_match، اقبله حتى لو لم ينجح validation
    # (لكن يفضل log warning)
```

**الخطورة:** 🔴🔴 حرجة
- 250+ سطر كود غير مستخدم
- النظام ليس آمناً من القرارات الخاطئة

---

### 🔴 النقطة 4: M3 و M4 لم يتم تنفيذهما (المشكلة الأساسية)

**M3: إصلاح parsing للـ manufacturer**

**المشكلة:**
```
Query:     "METHYL FOLATE 30 CAP ORCHIDIA"
           → brand = "METHYLFOLATE"

Candidate: "METHYL FOLATE (ORCHIDIA) 30 CAPS"
           → brand = "METHYLFOLATEORCHIDIA"

Result: different_brand ✗
```

المرشح الصحيح **يُرفض** قبل أن نصل لأي فحص آخر!

**M4: تنفيذ reject_extra_brand_token**

**المشكلة:**
- المفتاح موجود في config
- لكن **لا يوجد كود** يستخدمه في matching logic
- لا في `matching_penalties.py` ولا في `product_matching_acceptance.py`

**النتيجة:**
```
Query: "METHYL FOLATE ORCHIDIA"
Candidate: "METHYL FOLATE ORA"  ← ORA token إضافي
Result: accepted ✗  (يجب رفضه!)
```

**الخطورة:** 🔴🔴🔴 حرجة للغاية
- هذه هي **المشكلة الأساسية**
- بدون حلها، كل الإصلاحات الأخرى لن تكفي
- المرشح الصحيح لن يفوز أبداً

---

### 🟡 النقطة 5: الميزات معطلة افتراضياً

**الوضع الحالي:**
```python
# من config_models.py
enable_manufacturer_check: bool = False
reject_extra_brand_token: bool = False
```

```yaml
# من state/config.yaml
reject_extra_brand_token: false
# enable_manufacturer_check غير موجود (افتراضي False)
```

**التحليل:**
- القيم الافتراضية `False` **صحيحة** للأمان
- لأن التطبيق غير مكتمل
- لكن هذا يعني: حتى الكود الموجود لن يعمل

**الخطورة:** 🟡 متوسطة
- ليست مشكلة حالياً (لأن التطبيق غير جاهز)
- لكن يجب تفعيلها عندما تكتمل M3 و M4

---

## ملخص النقاط الحرجة

| النقطة | الخطورة | التأثير | الأولوية |
|---|---|---|---|
| القرار المحفوظ الخاطئ موجود | 🔴🔴🔴 | المشكلة تحدث في كل تشغيل | 1 |
| should_skip_auto_save غير مطبق | 🔴🔴 | المشكلة تعيد إنتاج نفسها | 2 |
| validation معطل | 🔴🔴 | 250+ سطر غير مستخدم | 3 |
| M3 و M4 لم يتم تنفيذهما | 🔴🔴🔴 | المشكلة الأساسية باقية | 1 |
| الميزات معطلة | 🟡 | حتى الكود الموجود لا يعمل | 5 |


---

## الفصل 4: اختبار المشكلة الحالية

### الهدف من هذا الفصل
إثبات أن المشكلة الأصلية **لا تزال موجودة** بعد التعديلات المنفذة.

---

### الاختبار 1: فحص القرار المحفوظ

**الأمر:**
```bash
grep "83165" docs/saved_corrected_items\(2\).csv
```

**النتيجة المتوقعة:** يجب ألا يظهر أي شيء (القرار محذوف)

**النتيجة الفعلية:**
```csv
83165,METHYL FOLATE 30 CAP ORCHIDIA,auto_matched,METHYL FOLATE ORA 30 CAPS,ميثيل فولات اورا 30 كبسول
```

**التقييم:** ❌ **فشل** - القرار الخاطئ لا يزال موجوداً

---

### الاختبار 2: فحص القيم الافتراضية

**الأمر:**
```python
python -c "from src.core.config.config_models import MatchingConfig; cfg = MatchingConfig(); print('enable_manufacturer_check:', cfg.enable_manufacturer_check); print('reject_extra_brand_token:', cfg.reject_extra_brand_token)"
```

**النتيجة المتوقعة:** يجب أن تكون إحداهما `True` على الأقل

**النتيجة الفعلية:**
```
enable_manufacturer_check: False
reject_extra_brand_token: False
```

**التقييم:** ⚠️ **متوقع** - القيم الافتراضية صحيحة لأن التطبيق غير مكتمل

---

### الاختبار 3: فحص استخدام should_skip_auto_save

**الأمر:**
```bash
grep -n "should_skip_auto_save" src/tawreed/order/tawreed_order_summary_build.py
```

**النتيجة المتوقعة:** يجب أن يظهر استدعاء في `_auto_save_verified_match`

**النتيجة الفعلية:**
```
(لا توجد نتائج)
```

**التقييم:** ❌ **فشل** - الدالة غير مستخدمة

---

### الاختبار 4: فحص تطبيق reject_extra_brand_token

**الأمر:**
```bash
grep -r "reject_extra_brand_token" src/core/matching/
```

**النتيجة المتوقعة:** يجب أن يظهر استخدام في matching logic

**النتيجة الفعلية:**
```
(لا توجد نتائج)
```

**التقييم:** ❌ **فشل** - لا يوجد logic يستخدم المفتاح

---

### الاختبار 5: فحص حالة validation

**الأمر:**
```bash
grep -A 3 "def _manual_review_id_match" src/core/manual_review/manual_review_helpers.py | head -10
```

**النتيجة المتوقعة:** يجب أن يكون validation مفعّلاً

**النتيجة الفعلية:**
```python
def _manual_review_id_match(...):
    # validation = _validate_manual_review_match(...)
    # if not validation["valid"]:
    #     return None
```

**التقييم:** ❌ **فشل** - validation معلّق

---

### الاختبار 6: محاكاة السلوك الفعلي

**السيناريو:** تشغيل المطابقة للصنف 83165

**الكود:**
```python
from src.core.matching.product_matching import explain_best_product_match
from src.core.config.config_models import MatchingConfig

query = "METHYL FOLATE 30 CAP ORCHIDIA"
candidates = [
    {"productName": "METHYL FOLATE (ORCHIDIA) 30 CAPS", "storeProductId": 123},
    {"productName": "METHYL FOLATE ORA 30 CAPS", "storeProductId": 456}
]

# مع default config
config = MatchingConfig()
result = explain_best_product_match(query, candidates, config)
```

**النتيجة المتوقعة:**
- المرشح الصحيح `(ORCHIDIA)` يجب أن يفوز
- أو على الأقل يُرسل للمراجعة اليدوية

**النتيجة الفعلية المتوقعة (بناءً على تحليل الكود):**
```
Candidate 1: METHYL FOLATE (ORCHIDIA) 30 CAPS
  score: 21.128814
  accepted: False
  reason: Semantic token conflict: different_brand

Candidate 2: METHYL FOLATE ORA 30 CAPS
  score: 19.103704
  accepted: True
  reason: Accepted best candidate because No extra numeric tokens.
```

**التقييم:** ❌ **فشل** - ORA سيفوز، المرشح الصحيح سيُرفض

---

### الاختبار 7: فحص الاختبارات الفاشلة

**الأمر:**
```bash
python -m pytest tests/test_manufacturer_mismatch.py -v
```

**النتيجة المتوقعة:** يجب أن يكون هناك اختبارات فاشلة توثق المشكلة

**النتيجة الفعلية:**
```
============================= test session starts =============================
tests/test_manufacturer_mismatch.py::...::test_orchidia_vs_ora_explicit_company_names PASSED
tests/test_manufacturer_mismatch.py::...::test_orchidia_vs_ora_produces_conflict_or_unsafe_match PASSED
tests/test_manufacturer_mismatch.py::...::test_same_company_different_spelling_no_conflict PASSED
tests/test_manufacturer_mismatch.py::...::test_missing_company_on_query_side_no_conflict PASSED
tests/test_manufacturer_mismatch.py::...::test_missing_company_on_candidate_side_no_conflict PASSED

============================== 5 passed in 1.10s ==============================
```

**التقييم:** ⚠️ **جميع الاختبارات تمر** - لكنها تختبر سيناريو مختلف (`enable_manufacturer_check=True` يدوياً)

---

## ملخص نتائج الاختبارات

| الاختبار | النتيجة | التقييم |
|---|---|---|
| القرار المحفوظ محذوف؟ | موجود | ❌ فشل |
| القيم الافتراضية مفعلة؟ | False | ⚠️ متوقع |
| should_skip_auto_save مستخدم؟ | لا | ❌ فشل |
| reject_extra_brand_token مطبق؟ | لا | ❌ فشل |
| validation مفعّل؟ | معلق | ❌ فشل |
| السلوك الفعلي صحيح؟ | ORA سيفوز | ❌ فشل |
| اختبارات فاشلة موجودة؟ | لا | ⚠️ متوقع |

---

## الاستنتاج النهائي

**جميع الاختبارات الحرجة فشلت.**

المشكلة الأصلية **لا تزال موجودة بنسبة 100%**:
1. ✗ القرار المحفوظ الخاطئ موجود
2. ✗ المرشح الصحيح سيُرفض
3. ✗ المرشح الخاطئ سيُقبل
4. ✗ auto-save سيحفظ الخطأ
5. ✗ المشكلة ستتكرر

**النظام سيتصرف بنفس الطريقة الخاطئة في التشغيل التالي.**


---

## الفصل 5: خطة الإصلاح الكاملة والمفصلة (الجزء 1 من 2)

> **ملاحظة:** هذه خطة واحدة مرتبة بحسب الأولوية من الأكثر أهمية للأقل أهمية.

---

## 🔴 المستوى 1: إصلاحات حرجة فورية (يجب تنفيذها أولاً)

### 1.1 حذف القرار المحفوظ الخاطئ للصنف 83165

**الأولوية:** 🔴🔴🔴 حرجة للغاية

**الملف:** `docs/saved_corrected_items(2).csv`

**الإجراء:**
```bash
# الطريقة 1: حذف السطر بالكامل
# حذف السطر 614 الذي يحتوي على:
# 83165,METHYL FOLATE 30 CAP ORCHIDIA,auto_matched,METHYL FOLATE ORA 30 CAPS,...

# الطريقة 2: تغيير decision_type إلى not_matching
# تعديل السطر 614 ليصبح:
# 83165,METHYL FOLATE 30 CAP ORCHIDIA,not_matching,,,
```

**التحقق:**
```bash
grep "83165" docs/saved_corrected_items\(2\).csv
# يجب ألا يظهر شيء، أو يظهر not_matching
```

**السبب:**
- هذا القرار يفرض ORA بدرجة 999
- يتجاوز جميع قواعد الأمان
- المشكلة ستحدث في كل تشغيل حتى يُحذف

**المدة المتوقعة:** 5 دقائق

---

### 1.2 تطبيق should_skip_auto_save في _auto_save_verified_match

**الأولوية:** 🔴🔴🔴 حرجة للغاية

**الملف:** `src/tawreed/order/tawreed_order_summary_build.py`

**التعديل المطلوب:**
```python
# السطور 61-74
def _auto_save_verified_match(item: Item, decision) -> None:
    """Auto-save verified matches to manual review store."""
    if not decision or not decision.best_match:
        return

    match = decision.best_match
    if match.score == 999.0 and "Approved by saved manual review" in (decision.final_reason or ""):
        return

    # ✓ إضافة هذا الفحص
    from src.core.manual_review.manual_review_runtime import should_skip_auto_save_verified_match
    
    if should_skip_auto_save_verified_match(item, match.data, decision.rejection_reason):
        return

    store = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB)
    if _preserve_existing_decision(store.lookup(item.code, item.name)):
        return

    _create_and_save_decision(item, match, store)
```

**التحقق:**
```python
# اختبار أن الدالة تُستدعى
python -c "from src.tawreed.order.tawreed_order_summary_build import _auto_save_verified_match; import inspect; print(inspect.getsource(_auto_save_verified_match))" | grep should_skip_auto_save
```

**السبب:**
- بدون هذا، auto-save سيحفظ matches خاطئة
- المشكلة ستعيد إنتاج نفسها
- حذف القرار الحالي لن يكون كافياً

**المدة المتوقعة:** 15 دقيقة

---

### 1.3 تفعيل validation في manual review matches (للقرارات التلقائية فقط)

**الأولوية:** 🔴🔴 حرجة

**الملف:** `src/core/manual_review/manual_review_helpers.py`

**التعديل المطلوب:**
```python
# السطور 210-230
def _manual_review_id_match(
    item: Item,
    decision: ManualReviewDecision,
    candidate: dict[str, Any],
) -> MatchDecision | None:
    """Match by store product ID."""
    if candidate_store_product_id(candidate) != decision.store_product_id:
        return None

    # ✓ تفعيل validation للقرارات التلقائية فقط
    validation = _validate_manual_review_match(item, decision, candidate)
    
    if decision.decision_type == "auto_matched" and not validation["valid"]:
        # القرار التلقائي فشل في validation - ارفضه
        return None
    
    # القرارات البشرية (approved_match) تُقبل حتى لو فشل validation
    # لكن يُفضل log warning
    if decision.decision_type == "approved_match" and not validation["valid"]:
        import logging
        logging.warning(
            f"Manual review decision for item {item.code} has validation issues: {validation['issues']}"
        )

    return MatchDecision(
        store_product_id=decision.store_product_id,
        product_name_en=decision.matched_product_name_en or "",
        product_name_ar=decision.matched_product_name_ar or "",
        score=999.0,
        reason=f"Approved by saved manual review (ID match). Decision type: {decision.decision_type}",
    )
```

**التعديل نفسه في `_manual_review_name_match`** (السطور 240-260)

**التحقق:**
```python
# اختبار أن validation غير معلق
python -c "from src.core.manual_review.manual_review_helpers import _manual_review_id_match; import inspect; src = inspect.getsource(_manual_review_id_match); print('validation enabled' if 'validation = _validate' in src else 'validation disabled')"
```

**السبب:**
- 250+ سطر validation غير مستخدم
- القرارات التلقائية الخاطئة تُقبل بدون فحص
- القرارات البشرية يمكن السماح لها، لكن مع تحذير

**المدة المتوقعة:** 30 دقيقة

---

## 🔴 المستوى 2: إصلاحات أساسية (المشكلة الجذرية)

### 2.1 إصلاح parsing للـ manufacturer في normalizer_matching_brand.py

**الأولوية:** 🔴🔴🔴 حرجة جداً

**الملف:** `src/core/drug_matching/normalization/normalizer_matching_brand.py`

**المشكلة:**
```
Query: "METHYL FOLATE 30 CAP ORCHIDIA" → brand = "METHYLFOLATE"
Candidate: "METHYL FOLATE (ORCHIDIA) 30 CAPS" → brand = "METHYLFOLATEORCHIDIA"
Result: different_brand ✗
```

**الحل المقترح:**

**أ) إضافة دالة لاستخراج manufacturer من الاسم:**
```python
def _extract_manufacturer_suffix(name: str) -> tuple[str, str | None]:
    """
    استخراج manufacturer من نهاية الاسم.
    
    Returns:
        (base_name, manufacturer)
    
    Examples:
        "METHYL FOLATE 30 CAP ORCHIDIA" → ("METHYL FOLATE 30 CAP", "ORCHIDIA")
        "METHYL FOLATE (ORCHIDIA) 30 CAPS" → ("METHYL FOLATE 30 CAPS", "ORCHIDIA")
    """
    import re
    
    # استخراج من الأقواس أولاً
    paren_match = re.search(r'\(([A-Z]+)\)', name.upper())
    if paren_match:
        manufacturer = paren_match.group(1)
        base_name = re.sub(r'\s*\([A-Z]+\)\s*', ' ', name, flags=re.IGNORECASE).strip()
        return base_name, manufacturer
    
    # استخراج آخر token قبل الأرقام إذا كان من قائمة معروفة
    KNOWN_MANUFACTURERS = {
        'ORCHIDIA', 'ORA', 'EVA', 'PHARCO', 'AMOUN', 'EIPICO', 
        'MARCYRL', 'SIGMA', 'SANOFI', 'NOVARTIS', 'PFIZER',
        # ... إضافة المزيد حسب الحاجة
    }
    
    tokens = name.upper().split()
    for i in range(len(tokens) - 1, -1, -1):
        if tokens[i].isdigit():
            continue
        if tokens[i] in KNOWN_MANUFACTURERS:
            manufacturer = tokens[i]
            base_name = ' '.join(tokens[:i] + tokens[i+1:])
            return base_name, manufacturer
        break
    
    return name, None
```

**ب) تعديل parsing ليستخدم الدالة الجديدة:**
```python
def parse_drug_with_manufacturer(name: str):
    """Parse drug name and separate manufacturer."""
    base_name, manufacturer = _extract_manufacturer_suffix(name)
    parsed = parse_drug(base_name)  # الدالة الأصلية
    parsed['manufacturer'] = manufacturer
    return parsed
```

**ج) تعديل component matching ليقارن manufacturer بشكل منفصل:**
```python
def components_match_with_manufacturer(query_parsed, candidate_parsed):
    """Compare components including manufacturer."""
    # مقارنة brand بدون manufacturer
    brand_match = _brand_match_check(query_parsed['brand'], candidate_parsed['brand'])
    
    # مقارنة manufacturer بشكل منفصل
    q_mfr = query_parsed.get('manufacturer')
    c_mfr = candidate_parsed.get('manufacturer')
    
    if q_mfr and c_mfr:
        # كلاهما لديه manufacturer - يجب أن يتطابقا
        if q_mfr != c_mfr:
            from src.core.identity.manufacturer_identity import manufacturer_conflict
            if manufacturer_conflict(q_mfr, c_mfr, threshold=0.85):
                return (False, 'different_manufacturer')
    
    return brand_match
```

**التحقق:**
```python
# اختبار
from src.core.drug_matching.normalization.normalizer_matching_brand import parse_drug_with_manufacturer, components_match_with_manufacturer

q = parse_drug_with_manufacturer("METHYL FOLATE 30 CAP ORCHIDIA")
c = parse_drug_with_manufacturer("METHYL FOLATE (ORCHIDIA) 30 CAPS")

print(f"Query: brand={q['brand']}, mfr={q['manufacturer']}")
print(f"Candidate: brand={c['brand']}, mfr={c['manufacturer']}")

match = components_match_with_manufacturer(q, c)
print(f"Match result: {match}")
# Expected: (True, 'ok') - يجب أن يتطابقا

ora = parse_drug_with_manufacturer("METHYL FOLATE ORA 30 CAPS")
match_ora = components_match_with_manufacturer(q, ora)
print(f"ORA match: {match_ora}")
# Expected: (False, 'different_manufacturer') - يجب أن يُرفض
```

**السبب:**
- هذه **المشكلة الأساسية**
- المرشح الصحيح لن يفوز أبداً بدون هذا الإصلاح
- أهم من أي شيء آخر

**المدة المتوقعة:** 2-3 ساعات (بما في ذلك الاختبارات)

**⚠️ ملاحظة حرجة:**
هذا التعديل قد يؤثر على حالات أخرى. يجب:
1. إضافة اختبارات شاملة
2. تشغيل جميع الاختبارات الموجودة
3. اختبار على عينة من الأصناف


---

## الفصل 5: خطة الإصلاح الكاملة والمفصلة (الجزء 2 من 2)

### 2.2 تنفيذ reject_extra_brand_token في matching logic

**الأولوية:** 🔴🔴 حرجة

**الملف:** `src/core/matching/matching_penalties.py`

**الإجراء:**

**أ) إضافة دالة للكشف عن extra brand tokens:**
```python
def has_extra_brand_token(query: str, candidate: str) -> tuple[bool, list[str]]:
    """
    فحص إذا كان المرشح يحتوي على brand token إضافي غير موجود في الاستعلام.
    
    Returns:
        (has_extra, extra_tokens)
    """
    from ..matching_types import GENERIC_TOKENS, FORM_TOKENS, UNIT_TOKENS
    
    query_tokens = canonical_tokens(query)
    candidate_tokens = canonical_tokens(candidate)
    
    # Tokens إضافية في المرشح
    extra = candidate_tokens - query_tokens
    
    # استثناء:
    # 1. أرقام
    # 2. وحدات (MG, ML, CAPS, TAB, etc.)
    # 3. forms (CREAM, SYRUP, etc.)
    # 4. generic tokens
    SAFE_TOKENS = GENERIC_TOKENS | FORM_TOKENS | UNIT_TOKENS
    
    distinguishing_extra = []
    for token in extra:
        if token.isdigit():
            continue
        if token in SAFE_TOKENS:
            continue
        # هذا token مميز إضافي
        distinguishing_extra.append(token)
    
    return (len(distinguishing_extra) > 0, distinguishing_extra)
```

**ب) تعديل compatibility_rejection_reason لاستخدامها:**
```python
def compatibility_rejection_reason(query: str, candidate: str, config=None) -> str:
    """Return a deterministic rejection reason for unsafe lexical variants."""
    details = _token_details(query, candidate)
    if details["conflicts"]:
        return _conflict_reason(details["conflicts"])
    
    # ✓ إضافة فحص extra brand token
    if config and hasattr(config, 'reject_extra_brand_token') and config.reject_extra_brand_token:
        has_extra, extra_tokens = has_extra_brand_token(query, candidate)
        if has_extra:
            tokens_str = ", ".join(sorted(extra_tokens))
            return f"Candidate has unrequested brand token: {tokens_str}"
    
    if details["extra_distinguishing"]:
        tokens = ", ".join(sorted(details["extra_distinguishing"]))
        return f"Candidate has unrequested distinguishing token: {tokens}"
    
    return ""
```

**ج) تمرير config إلى compatibility_rejection_reason:**
في `src/core/matching/product_matching_acceptance.py`:
```python
def _check_rejections(
    score_query: str,
    candidate: dict[str, Any],
    config: dict[str, Any] | MatchingConfig | None = None,
    skip_components: bool = False,
) -> tuple[bool, str]:
    """Check all rejection criteria and return (is_rejected, reason)."""
    config = config or {}
    checks = [
        _candidate_variant_rejection(score_query, candidate),
        compatibility_rejection_reason(score_query, _candidate_english_name(candidate), config),  # ← تمرير config
    ]
    # ... بقية الكود
```

**التحقق:**
```python
from src.core.matching.matching_penalties import has_extra_brand_token, compatibility_rejection_reason
from src.core.config.config_models import MatchingConfig

# اختبار
query = "METHYL FOLATE ORCHIDIA"
candidate_ora = "METHYL FOLATE ORA"
candidate_orchidia = "METHYL FOLATE ORCHIDIA"

config_enabled = MatchingConfig(reject_extra_brand_token=True)
config_disabled = MatchingConfig(reject_extra_brand_token=False)

print("ORA with enabled:", compatibility_rejection_reason(query, candidate_ora, config_enabled))
# Expected: "Candidate has unrequested brand token: ORA"

print("ORA with disabled:", compatibility_rejection_reason(query, candidate_ora, config_disabled))
# Expected: "" (لا رفض)

print("ORCHIDIA:", compatibility_rejection_reason(query, candidate_orchidia, config_enabled))
# Expected: "" (لا رفض - المرشح صحيح)
```

**السبب:**
- المفتاح موجود لكن غير مستخدم
- بدون هذا، ORA سيُقبل كـ "مطابقة جيدة"

**المدة المتوقعة:** 1-2 ساعة

---

## 🟡 المستوى 3: اختبارات وتوثيق

### 3.1 إضافة اختبارات فاشلة (Test-Driven Development)

**الأولوية:** 🟡 متوسطة-عالية

**الملف:** `tests/test_manufacturer_mismatch.py`

**الإجراء:**
```python
class TestDefaultConfigBehavior:
    """اختبارات تستخدم default config من YAML."""
    
    def test_default_config_should_reject_ora_for_orchidia(self):
        """يجب أن يرفض ORA عندما الطلب يحتوي ORCHIDIA."""
        from src.core.config.config_factory import build_matching_config
        from src.core.matching.product_matching import explain_best_product_match
        
        config = build_matching_config()  # من YAML
        query = "METHYL FOLATE 30 CAP ORCHIDIA"
        candidates = [
            {"productName": "METHYL FOLATE ORA 30 CAPS", "storeProductId": 456}
        ]
        
        result = explain_best_product_match(query, candidates, config)
        
        # يجب أن يُرفض أو يُرسل للمراجعة اليدوية
        assert not result.accepted or result.requires_manual_review
    
    def test_orchidia_candidate_should_win_over_ora(self):
        """المرشح الصحيح ORCHIDIA يجب أن يفوز على ORA."""
        config = build_matching_config()
        query = "METHYL FOLATE 30 CAP ORCHIDIA"
        candidates = [
            {"productName": "METHYL FOLATE (ORCHIDIA) 30 CAPS", "storeProductId": 123},
            {"productName": "METHYL FOLATE ORA 30 CAPS", "storeProductId": 456}
        ]
        
        result = explain_best_product_match(query, candidates, config)
        
        # ORCHIDIA يجب أن يفوز
        assert result.best_match.data["storeProductId"] == 123
        assert "ORCHIDIA" in result.best_match.data["productName"]

class TestAutoSaveValidation:
    """اختبارات لـ auto-save safety."""
    
    def test_auto_save_should_skip_manufacturer_conflict(self):
        """auto-save يجب أن يتخطى matches عليها manufacturer conflict."""
        from src.core.manual_review.manual_review_runtime import should_skip_auto_save_verified_match
        from src.core.ordering.item import Item
        
        item = Item(code=83165, name="METHYL FOLATE 30 CAP ORCHIDIA", quantity=1)
        ora_candidate = {
            "productName": "METHYL FOLATE ORA 30 CAPS",
            "storeProductId": 456
        }
        
        should_skip = should_skip_auto_save_verified_match(item, ora_candidate)
        
        # يجب أن يتخطى الحفظ
        assert should_skip == True

class TestSavedDecisionValidation:
    """اختبارات لـ saved decision validation."""
    
    def test_auto_matched_with_conflict_should_be_rejected(self):
        """قرار auto_matched خاطئ يجب أن يُرفض."""
        from src.core.manual_review.manual_review_helpers import _manual_review_id_match
        from src.core.manual_review.manual_review_store import ManualReviewDecision
        from src.core.ordering.item import Item
        
        item = Item(code=83165, name="METHYL FOLATE 30 CAP ORCHIDIA", quantity=1)
        decision = ManualReviewDecision(
            decision_type="auto_matched",
            store_product_id=456,
            matched_product_name_en="METHYL FOLATE ORA 30 CAPS"
        )
        ora_candidate = {
            "storeProductId": 456,
            "productName": "METHYL FOLATE ORA 30 CAPS"
        }
        
        result = _manual_review_id_match(item, decision, ora_candidate)
        
        # يجب أن يُرفض (None)
        assert result is None
```

**التحقق:**
```bash
python -m pytest tests/test_manufacturer_mismatch.py::TestDefaultConfigBehavior -v
# يجب أن تفشل قبل الإصلاح وتنجح بعده
```

**السبب:**
- TDD يضمن أن الإصلاح يحل المشكلة
- يمنع regression في المستقبل

**المدة المتوقعة:** 1 ساعة

---

### 3.2 تفعيل المفاتيح في config بعد اكتمال التطبيق

**الأولوية:** 🟡 متوسطة

**الملف:** `state/config.yaml`

**الإجراء:**
```yaml
matching:
  # ... مفاتيح أخرى
  
  # ✓ تفعيل بعد إكمال M3
  enable_manufacturer_check: true
  manufacturer_match_threshold: 0.85
  
  # ✓ تفعيل بعد إكمال M4
  reject_extra_brand_token: true
```

**⚠️ تحذير:**
- **لا تفعّل هذه المفاتيح قبل إكمال M3 و M4**
- التفعيل المبكر قد يسبب false positives

**التحقق:**
```python
from src.core.config.config_factory import build_matching_config
config = build_matching_config()
print("enable_manufacturer_check:", config.enable_manufacturer_check)
print("reject_extra_brand_token:", config.reject_extra_brand_token)
# Expected: True, True
```

**المدة المتوقعة:** 5 دقائق

---

## 🟢 المستوى 4: تحسينات وضمان الجودة

### 4.1 تشغيل جميع الاختبارات

**الأولوية:** 🟢 مهمة

**الأوامر:**
```bash
# اختبارات المطابقة
python -m pytest tests/test_manufacturer_mismatch.py -v
python -m pytest tests/test_product_matching.py -v

# اختبارات manual review
python -m pytest tests/core/manual_review/ -v

# اختبارات شاملة
python -m pytest tests/ -v --ignore=tools
```

**معيار النجاح:**
- جميع الاختبارات تمر
- لا توجد regression

**المدة المتوقعة:** 30 دقيقة

---

### 4.2 اختبار على عينة من الأصناف

**الأولوية:** 🟢 مهمة

**الإجراء:**
```bash
# إنشاء ملف Excel بالصنف 83165 فقط
# ثم تشغيل match-only
python run.py order --profile wardany --excel test_83165.xlsx --match-only --execution-mode auto
```

**التحقق من النتائج:**
```bash
# فحص order_item_summary
# يجب أن يكون:
# - matched_product_name_en = "METHYL FOLATE (ORCHIDIA) 30 CAPS"
# - أو manual-review-required
# - وليس "METHYL FOLATE ORA 30 CAPS"
```

**المدة المتوقعة:** 30 دقيقة

---

### 4.3 مراجعة وتحديث التوثيق

**الأولوية:** 🟢 منخفضة

**الإجراءات:**
1. تحديث `config.example.yaml` بتعليقات إضافية
2. توثيق القرار في `docs/` إذا لزم الأمر
3. إضافة تعليقات في الكود الجديد

**المدة المتوقعة:** 30 دقيقة

---

## جدول ملخص الخطة الكاملة

| # | المهمة | الأولوية | المدة | التبعيات |
|---|---|---|---|---|
| 1.1 | حذف القرار المحفوظ الخاطئ | 🔴🔴🔴 | 5 دقائق | - |
| 1.2 | تطبيق should_skip_auto_save | 🔴🔴🔴 | 15 دقيقة | - |
| 1.3 | تفعيل validation للقرارات التلقائية | 🔴🔴 | 30 دقيقة | - |
| 2.1 | إصلاح parsing للـ manufacturer | 🔴🔴🔴 | 2-3 ساعات | - |
| 2.2 | تنفيذ reject_extra_brand_token | 🔴🔴 | 1-2 ساعة | - |
| 3.1 | إضافة اختبارات فاشلة | 🟡 | 1 ساعة | 2.1, 2.2 |
| 3.2 | تفعيل المفاتيح في config | 🟡 | 5 دقائق | 2.1, 2.2 |
| 4.1 | تشغيل جميع الاختبارات | 🟢 | 30 دقيقة | الكل |
| 4.2 | اختبار على عينة | 🟢 | 30 دقيقة | الكل |
| 4.3 | تحديث التوثيق | 🟢 | 30 دقيقة | الكل |

**المدة الإجمالية المتوقعة:** 6-8 ساعات عمل

---

## ترتيب التنفيذ الموصى به

### اليوم 1 (2-3 ساعات):
1. ✓ 1.1 حذف القرار المحفوظ (5 دقائق)
2. ✓ 1.2 تطبيق should_skip_auto_save (15 دقيقة)
3. ✓ 1.3 تفعيل validation (30 دقيقة)
4. ✓ 2.1 إصلاح parsing (2-3 ساعات)

### اليوم 2 (2-3 ساعات):
5. ✓ 2.2 تنفيذ reject_extra_brand_token (1-2 ساعة)
6. ✓ 3.1 إضافة اختبارات (1 ساعة)
7. ✓ 4.1 تشغيل الاختبارات (30 دقيقة)

### اليوم 3 (1 ساعة):
8. ✓ 3.2 تفعيل المفاتيح (5 دقائق)
9. ✓ 4.2 اختبار على عينة (30 دقيقة)
10. ✓ 4.3 تحديث التوثيق (30 دقيقة)

---

## معايير النجاح النهائية

✅ **المشكلة محلولة عندما:**
1. القرار المحفوظ الخاطئ محذوف
2. المرشح الصحيح `METHYL FOLATE (ORCHIDIA)` يفوز
3. المرشح الخاطئ `METHYL FOLATE ORA` يُرفض
4. auto-save لا يحفظ matches خاطئة
5. جميع الاختبارات تمر
6. اختبار match-only ينجح للصنف 83165

---

**انتهت خطة الإصلاح الكاملة.**

