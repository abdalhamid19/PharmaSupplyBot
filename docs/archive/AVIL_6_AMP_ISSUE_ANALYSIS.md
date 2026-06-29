# تقرير تحليل مشكلة: عدم مطابقة صنف AVIL 6 AMP

**تاريخ التقرير:** 2026-06-22  
**رقم التشغيل المشكل:** 20260622_1535  
**كود الصنف:** 73396  
**اسم الصنف:** AVIL 6 AMP  
**المنتج المتوقع:** AVIL 45.5 MG / 2 ML 6 I.M. AMPS. (افيل 45.5 مجم / 2 مل 6 امبول)  

---

## 1. ملخص المشكلة

تم إدخال صنف **AVIL 6 AMP** في النظام، لكن النتيجة كانت **no-results** رغم أن المنتج المطابق موجود فعلاً على موقع توريد باسم **AVIL 45.5 MG / 2 ML 6 I.M. AMPS.** وحتى بعد تصحيحه يدوياً في manual_review سابقاً، لم يُطبّق التصحيح في التشغيل الحالي.

### النتيجة الفعلية:
```
item_code: 73396
item_name: AVIL 6 AMP
status: no-results
reason: No decisive match found for 'AVIL 6 AMP' after 3 queries.
final_reason: Candidate has unrequested numeric token: 2, 45, 5
```

### المنتج المرفوض:
```
product_name_en: AVIL 45.5 MG / 2 ML 6 I.M. AMPS.
product_name_ar: افيل 45.5 مجم / 2 مل 6 امبول
store_product_id: 2640615
available_quantity: 147
total_score: 14.832
sequence_score: 0.526
overlap_score: 0.900
numeric_overlap: 1.000
rejection_reason: Candidate has unrequested numeric token: 2, 45, 5
```

---

## 2. التحليل التفصيلي للمشكلة

### 2.1 آلية توليد استعلامات البحث (Query Generation)

عند إدخال **AVIL 6 AMP**، يقوم النظام بتوليد 3 queries أساسية:
1. `AVIL 6 AMP` (الاسم الكامل)
2. `AVIL 6` (بدون الـ form)
3. `AVIL` (البراند فقط)

**ملاحظة:** لا توجد queries إضافية بالتركيز (dosage) لأن النظام يعتبر الـ `6` كمية (qty) وليس تركيز.

### 2.2 تحليل الصنف بواسطة parse_drug

#### Query: "AVIL 6 AMP"
```python
Brand: AVIL
Form: AMP
Qty: 6              ← النظام يعتبر 6 كمية
Dosage nums: ()     ← فارغ!
Dosage units: ()    ← فارغ!
Volume: 
```

#### Candidate: "AVIL 45.5 MG / 2 ML 6 I.M. AMPS."
```python
Brand: AVIL
Form: AMP
Qty: 
Dosage nums: ('45.5',)      ← يحتوي على تركيز
Dosage units: ('MG/ML',)
Volume: 2                    ← حجم 2 مل
```

### 2.3 الأرقام المستخرجة (Numeric Tokens)

- **Query normalized:** `AVIL 6 AMP`
  - Numeric tokens: `{6}`

- **Candidate normalized:** `AVIL 45 5 MG 2 ML 6 I M AMPS`
  - Numeric tokens: `{45, 5, 2, 6}`

- **Extra tokens (الأرقام الإضافية):** `{45, 5, 2}`
  - `45` و `5` من التركيز 45.5 MG
  - `2` من الحجم 2 ML

### 2.4 فحص التوافق (Components Match)

```python
components_match(query_parsed, candidate_parsed)
→ (True, 'ok')
```

النظام يعتبرهما **متوافقين** من حيث المكونات الصيدلانية.

### 2.5 منطق رفض الأرقام الإضافية

الكود المسؤول عن رفض المطابقة في `product_matching.py`:

```python
def _numeric_safe_acceptance(...):
    extra = _unrequested_numeric_tokens(query, cand_name)
    extra = _ignore_component_safe_numeric_tokens(extra, query, cand_name)
    if acceptance[0] and acceptance[1] != "exact_normalized_name_match" and extra:
        tokens = ", ".join(sorted(extra))
        return False, "", f"Candidate has unrequested numeric token: {tokens}"
    return acceptance
```

### 2.6 السبب الجذري: فشل _safe_omitted_injection_volume

الدالة `_safe_omitted_injection_volume` مصممة لقبول الأرقام الإضافية عندما تكون injection volume، لكنها تفشل هنا بسبب:

```python
def _safe_omitted_injection_volume(tokens: set[str], requested, offered) -> bool:
    if not requested.dosage_nums or not offered.dosage_nums:  ← هنا المشكلة!
        return False
    if not offered.volume or offered.volume not in tokens:
        return False
    if requested.volume or requested.form not in {"AMP", "VIAL"}:
        return False
    return offered.form in {"AMP", "VIAL"}
```

**الشرط الأول يفشل:**
- `requested.dosage_nums` فارغ → `not requested.dosage_nums = True`
- لذلك ترجع الدالة `False` مباشرة

**النتيجة:** الأرقام الإضافية `{2, 45, 5}` تُعتبر "unrequested" ويتم رفض المطابقة.

---

## 3. الأسباب المحتملة (مرتبة حسب الأولوية)

### السبب الرئيسي ⭐⭐⭐⭐⭐ (مؤكد 100%)
**منطق `_safe_omitted_injection_volume` يتطلب وجود dosage في Query**

- الدالة تفترض أن الـ query يحتوي على dosage (مثل "AVIL 45.5 MG 6 AMP")
- لكن في حالتنا، الـ query هو "AVIL 6 AMP" فقط (بدون dosage)
- الشرط `if not requested.dosage_nums` يفشل مباشرة
- هذا تصميم غير مكتمل للحالات التي يكون فيها الـ brand + qty + form فقط

### أسباب ثانوية:

#### 2. عدم تطبيق manual_review السابق ⭐⭐⭐⭐
- النظام يستخدم **CockroachDB Cloud** (وليس SQLite محلية)
- التصحيح اليدوي السابق الذي ذكرته (approved_match لـ AVIL) **غير موجود في CockroachDB**
- يجب إضافة التصحيح إلى CockroachDB باستخدام `ManualReviewStore.upsert()`
- النظام يقرأ من CockroachDB عبر `src/core/manual_review_store.py`

#### 3. parse_drug لا يتعرف على الـ 6 كجزء من اسم المنتج ⭐⭐⭐
- النظام يعتبر "6" في "AVIL 6 AMP" كمية (qty)
- بينما في الحقيقة، "AVIL 6 AMP" هو اسم تجاري يشير إلى عبوة بها 6 امبولات
- الـ 6 ليس dosage ولا qty حقيقية، بل جزء من هوية المنتج

#### 4. عدم توليد query بديل مع dosage ⭐⭐
- النظام لم يولد query مثل "AVIL 45.5 AMP" أو "AVIL 45 AMP"
- `category_queries()` تعتمد على وجود dosage في parse، وهو غير موجود
- لو كان النظام يبحث بـ "AVIL AMP" فقط، قد يكون أفضل

#### 5. عدم استخدام aggressive matching ⭐
- قد يكون هناك مستوى matching أعلى يتجاهل الأرقام في حالات معينة
- لكن النظام الحالي صارم جداً في رفض unrequested numeric tokens

---

## 4. الحلول المقترحة (مع خطة التنفيذ)

### الحل الأول (الموصى به): تحسين منطق `_safe_omitted_injection_volume` ⭐⭐⭐⭐⭐

**الوصف:**  
تعديل الدالة لقبول injection volume حتى لو لم يكن الـ query يحتوي على dosage.

**المنطق الجديد:**
```python
def _safe_omitted_injection_volume(tokens: set[str], requested, offered) -> bool:
    # الشرط القديم: يتطلب dosage في كلا الطرفين
    # الشرط الجديد: يكفي أن يكون offered يحتوي على dosage + volume، 
    #                 والـ requested هو AMP/VIAL بدون dosage
    
    # حالة 1: Query + Candidate كلاهما يحتوي dosage (المنطق القديم)
    if requested.dosage_nums and offered.dosage_nums:
        if not offered.volume or offered.volume not in tokens:
            return False
        if requested.volume or requested.form not in {"AMP", "VIAL"}:
            return False
        return offered.form in {"AMP", "VIAL"}
    
    # حالة 2 (جديدة): Query بدون dosage، لكن Candidate يحتوي dosage + volume
    if not requested.dosage_nums and offered.dosage_nums and offered.volume:
        # التحقق أن الأرقام الإضافية هي dosage + volume فقط
        dosage_volume_tokens = set()
        
        # استخراج أرقام dosage
        for num in offered.dosage_nums:
            dosage_volume_tokens.update(_numeric_tokens(num))
        
        # إضافة volume
        if offered.volume:
            dosage_volume_tokens.add(offered.volume)
        
        # التحقق أن extra tokens محصورة في dosage + volume
        if tokens.issubset(dosage_volume_tokens):
            if requested.form in {"AMP", "VIAL"} and offered.form in {"AMP", "VIAL"}:
                return True
    
    return False
```

**خطوات التنفيذ:**
1. ✅ فتح `src/core/product_matching.py`
2. ✅ تحديد موقع `_safe_omitted_injection_volume` (حول السطر 862)
3. ✅ تعديل المنطق حسب الكود أعلاه
4. ✅ إضافة helper function `_numeric_tokens` إذا لم تكن موجودة
5. ✅ كتابة unit test للحالة الجديدة
6. ✅ تشغيل الاختبارات الحالية للتأكد من عدم كسر السلوك القديم
7. ✅ اختبار على AVIL 6 AMP

**التأثير:**
- ✅ يحل المشكلة بشكل مباشر
- ✅ لا يؤثر على الحالات الأخرى
- ✅ منطقي من الناحية الصيدلانية
- ⚠️ قد يقبل بعض المطابقات غير الصحيحة إذا لم نكن حذرين

**المخاطر:**
- متوسطة: قد يقبل منتجات بتركيزات مختلفة إذا لم يُضبط المنطق جيداً
- يحتاج testing مكثف على أصناف مختلفة

---

### الحل الثاني: تحسين parse_drug للتعرف على أنماط "BRAND QTY FORM" ⭐⭐⭐⭐

**الوصف:**  
تعليم `parse_drug` أن يتعرف على أنماط مثل "AVIL 6 AMP" كمنتج كامل، وليس dosage.

**المنطق:**
```python
# في normalizer.py، داخل parse_drug
# بعد استخراج Brand و Form
# إذا كان Pattern هو: BRAND + NUMBER + FORM (بدون units)
# اعتبر الـ NUMBER كـ qty وليس dosage

# مثال:
# AVIL 6 AMP → brand=AVIL, qty=6, form=AMP
# AVIL 45.5 MG 6 AMP → brand=AVIL, dosage=45.5MG, qty=6, form=AMP
```

**خطوات التنفيذ:**
1. فتح `src/core/drug_matching/normalizer.py`
2. تحديد موقع `parse_drug` function
3. إضافة منطق pattern matching للحالات البسيطة
4. التأكد من عدم تعارض مع الحالات الأخرى
5. إضافة unit tests شاملة

**التأثير:**
- ✅ يحسن فهم النظام بشكل عام
- ✅ يساعد في توليد queries أفضل
- ⚠️ معقد ويحتاج testing مكثف

**المخاطر:**
- عالية: قد يكسر parsing لأصناف أخرى
- يحتاج refactoring كبير

---

### الحل الثالث: إضافة تصحيح AVIL إلى CockroachDB ⭐⭐⭐⭐⭐

**الوصف:**  
إضافة التصحيح اليدوي لـ AVIL 6 AMP إلى CockroachDB Cloud باستخدام النظام الموجود.

**خطوات التنفيذ:**
1. ✅ استخدام `ManualReviewStore` من `src/core/manual_review_store.py`
2. ✅ إنشاء `ManualReviewDecision` للصنف AVIL
3. ✅ استدعاء `store.upsert()` لحفظ التصحيح
4. ✅ التحقق من الحفظ بـ `store.lookup()`

**الكود:**
```python
from src.core.manual_review_store import ManualReviewStore, ManualReviewDecision

# إنشاء store متصل بـ CockroachDB
store = ManualReviewStore()

# إنشاء التصحيح
avil_correction = ManualReviewDecision(
    item_code="73396",
    item_name="AVIL 6 AMP",
    approved=True,
    correct_store_product_id="2640615",
    correct_product_name="AVIL 45.5 MG / 2 ML 6 I.M. AMPS.",
    correct_product_name_ar="افيل 45.5 مجم / 2 مل 6 امبول",
    run_id="20260622_1535",
    manual_decision="approved_match"
)

# حفظ في CockroachDB
store.upsert(avil_correction)

# التحقق
saved = store.lookup("73396", "AVIL 6 AMP")
print(f"Saved: {saved}")
```

**التأثير:**
- ✅ يحل المشكلة فوراً لهذا الصنف
- ✅ يضمن عدم تكرار المشكلة مستقبلاً
- ✅ يستخدم النظام الموجود (CockroachDB)
- ✅ يوفر وقت المراجعة اليدوية

**المخاطر:**
- منخفضة جداً (النظام موجود ومختبر)

---

### الحل الرابع: إضافة exception rule خاص بـ AVIL ⭐⭐

**الوصف:**  
إضافة قاعدة خاصة في matching rules لـ AVIL.

**المنطق:**
```python
# في product_matching.py أو matching_rules.py
BRAND_QTY_EXCEPTIONS = {
    "AVIL": {
        "6 AMP": "2640615",  # AVIL 45.5 MG / 2 ML 6 I.M. AMPS
    }
}

def _check_brand_qty_exception(query: str) -> str | None:
    for brand, patterns in BRAND_QTY_EXCEPTIONS.items():
        if brand in query.upper():
            for pattern, store_product_id in patterns.items():
                if pattern in query.upper():
                    return store_product_id
    return None
```

**التأثير:**
- ✅ حل سريع ومضمون
- ❌ لا يحل المشكلة الجذرية
- ❌ يحتاج صيانة يدوية لكل حالة مشابهة

---

### الحل الخامس: تحسين query generation ⭐⭐⭐

**الوصف:**  
توليد queries إضافية مع تجاهل الأرقام.

**المنطق:**
```python
def _search_queries_for_item(item: Item) -> list[str]:
    queries = []
    
    # Query أساسي
    queries.append("AVIL 6 AMP")
    
    # Query بدون أرقام (جديد)
    queries.append("AVIL AMP")
    
    # Query مع form فقط
    queries.append("AVIL")
    
    return queries
```

**التأثير:**
- ✅ يزيد فرص إيجاد المطابقات
- ⚠️ قد يرجع نتائج أقل دقة
- ⚠️ يزيد عدد API calls

---

## 5. خطة التنفيذ الموصى بها

### المرحلة الأولى: حل فوري (15 دقيقة)

1. **إضافة تصحيح AVIL إلى CockroachDB** (الحل 3)
   - استخدام `ManualReviewStore.upsert()`
   - إضافة ManualReviewDecision للصنف
   - التحقق من الحفظ
   - **النتيجة:** المشكلة محلولة فوراً لـ AVIL

### المرحلة الثانية: حل دائم (3-5 ساعات)

2. **تحسين `_safe_omitted_injection_volume`** (الحل 1)
   - تعديل الكود حسب المنطق الجديد
   - كتابة unit tests شاملة
   - اختبار على 20+ صنف injection
   - **النتيجة:** المشكلة محلولة بشكل عام للحالات المشابهة

### المرحلة الثالثة: تحسينات إضافية (1-2 أيام)

3. **تحسين parse_drug** (الحل 2 - اختياري)
   - إذا ظهرت حالات أخرى مشابهة
   
4. **تحسين query generation** (الحل 5 - اختياري)
   - لزيادة معدل الإيجاد

---

## 6. الاختبارات المطلوبة

### Unit Tests

```python
def test_safe_omitted_injection_volume_without_query_dosage():
    """Test AVIL 6 AMP case"""
    query = "AVIL 6 AMP"
    candidate = "AVIL 45.5 MG / 2 ML 6 I.M. AMPS."
    
    requested = parse_drug(query)
    offered = parse_drug(candidate)
    tokens = {'45', '5', '2'}
    
    result = _safe_omitted_injection_volume(tokens, requested, offered)
    assert result == True, "Should accept injection volume when query has no dosage"

def test_existing_injection_cases_still_work():
    """Ensure old behavior is preserved"""
    query = "INSULIN 100 IU VIAL"
    candidate = "INSULIN 100 IU / 3 ML VIAL"
    
    requested = parse_drug(query)
    offered = parse_drug(candidate)
    tokens = {'3'}
    
    result = _safe_omitted_injection_volume(tokens, requested, offered)
    assert result == True, "Should still work for queries with dosage"
```

### Integration Tests

1. تشغيل order على ملف يحتوي AVIL 6 AMP
2. التأكد من المطابقة الناجحة
3. التحقق من matching_trace والتأكد من عدم رفض بسبب numeric tokens

---

## 7. المخاطر المحتملة

| المخاطر | الاحتمالية | التأثير | الحل |
|---------|------------|---------|------|
| الحل 1 يقبل مطابقات خاطئة | متوسط | عالي | Unit tests مكثفة + مراجعة يدوية |
| الحل 2 يكسر parsing لأصناف أخرى | عالي | عالي | Regression tests شاملة |
| قاعدة البيانات تفقد البيانات | منخفض | متوسط | Backup دوري |
| النظام يبطئ بسبب queries إضافية | منخفض | منخفض | Query caching |

---

## 8. الخلاصة

### الأسباب الرئيسية للمشكلة:

1. ✅ **منطق `_safe_omitted_injection_volume` غير مكتمل** - يفشل عندما Query بدون dosage
2. ✅ **التصحيح اليدوي غير موجود في CockroachDB** - يجب إضافته
3. ✅ **parse_drug يسيء فهم "AVIL 6 AMP"** - يعتبر 6 كمية بدل جزء من الاسم

### الحل الموصى به:

**جمع بين الحل 1 و 3:**
- **فوري:** إضافة تصحيح AVIL إلى CockroachDB باستخدام `ManualReviewStore`
- **دائم:** تحسين `_safe_omitted_injection_volume` لقبول injection volumes حتى بدون dosage في Query

### الأولوية:

1. 🔴 **عاجل:** إضافة AVIL إلى CockroachDB (15 دقيقة)
2. 🟠 **مهم:** تحسين `_safe_omitted_injection_volume` (3-4 ساعات)
3. 🟡 **تحسين:** parse_drug و query generation (اختياري)

---

## 9. الملفات المعنية

| الملف | الغرض | التعديل المطلوب |
|-------|-------|-----------------|
| `src/core/product_matching.py` | منطق المطابقة | تعديل `_safe_omitted_injection_volume` |
| `src/core/manual_review_store.py` | CockroachDB store | استخدام `upsert()` لإضافة AVIL |
| `src/core/database.py` | الاتصال بـ CockroachDB | (لا يحتاج تعديل) |
| `src/core/drug_matching/normalizer.py` | Parsing | (اختياري) تحسين pattern recognition |
| `src/core/search_query_templates.py` | Query generation | (اختياري) إضافة queries بديلة |

---

## 10. ملاحظات إضافية

- المنتج **AVIL 45.5 MG / 2 ML 6 I.M. AMPS** موجود فعلاً على توريد
- لديه `available_quantity = 147` (كمية جيدة)
- الـ score كان عالي جداً `14.832` و `overlap_score = 0.9`
- المطابقة كانت شبه مثالية، لكن رُفضت فقط بسبب الأرقام الإضافية
- التصحيح اليدوي السابق المذكور **غير موجود في CockroachDB** حالياً
- النظام يستخدم **CockroachDB Cloud** للتخزين المركزي (وليس SQLite محلية)

---

**تم إعداد هذا التقرير بناءً على:**
- فحص artifacts التشغيل 20260622_1535
- تحليل كود product_matching.py
- اختبار parse_drug على الصنف
- فحص قاعدة بيانات manual_review
- مراجعة matching_trace و logs

**المحلل:** Kiro AI  
**التاريخ:** 2026-06-22
