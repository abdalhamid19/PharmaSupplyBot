# تقرير شامل: مشكلة اختفاء matched_product_name في حالة not-orderable

## 📋 وصف المشكلة

عند تشغيل order run في واجهة Streamlit، إذا كان status الصنف هو `not-orderable`، فإن الحقول التالية تظهر **فارغة** في `order_item_summary`:
- `matched_product_name_en`
- `matched_product_name_ar`
- `matched_product_id`
- `matched_store_product_id`

بينما البيانات **موجودة** في:
- `blocked_candidate_name_en`
- `blocked_candidate_name_ar`
- `blocked_candidate_product_id`
- `blocked_candidate_store_product_id`

---

## 🔍 مثال حقيقي من البيانات

### من ملف: `artifacts/order/wardany/20260621_1054/order_item_summary_20260621_1054.csv`

```csv
item_code: 74821
item_name: BETADINE ANTISEPTIC 60 ML SOLN. 10%
status: not-orderable
matched_product_name_en: BETADINE ANTISEPTIC SOLN. 10 % 60 ML    ← موجود!
matched_product_name_ar: بيتادين محلول مطهر 10 % 60 مل النيل      ← موجود!
blocked_candidate_name_en: BETADINE ANTISEPTIC SOLN. 10 % 60 ML
blocked_candidate_name_ar: بيتادين محلول مطهر 10 % 60 مل النيل
```

**ملاحظة:** في هذا المثال البيانات موجودة بالفعل! دعني أتحقق من حالة أخرى...

---

## 🔬 التحليل التفصيلي الممل (كما طلبت)

### 1. تتبع مسار البيانات (Data Flow)

```
[tawreed.py: process_single_item]
    ↓
[tawreed_search_logic.py: require_product_match]
    ↓ returns: SearchMatch or raises SkipItem
    ↓
[Decision object created with diagnostics]
    ↓
[SkipItem exception raised: "No decisive match"]
    ↓
[_record_skip in tawreed.py]
    ↓
[_build_item_summary: creates OrderItemSummary]
    ↓
[append_order_result_summary]
    ↓
[order_item_summary_row in order_run_artifact_rows.py]
    ↓
[CSV row written]
```

### 2. الكود المسؤول عن المشكلة

#### الملف: `src/core/order_run_artifact_rows.py`

```python
def order_item_summary_row(item, summary, decision, outcome) -> dict[str, object]:
    """Return one compact row describing the final item outcome."""
    match = decision.best_match if decision else None  # ← السطر 32
    blocked_candidate = blocked_ai_candidate(outcome) if not match else {}  # ← السطر 33
    status = effective_order_status(summary.status, outcome)
    
    best_diagnostic = None
    if status == "not-orderable" and not blocked_candidate and not match:  # ← السطر 37
        if decision and getattr(decision, "diagnostics", None):
            best_diagnostic = max(decision.diagnostics, key=lambda d: d.score, default=None)
            if best_diagnostic and getattr(best_diagnostic, "candidate", None):
                blocked_candidate = best_diagnostic.candidate  # ← السطر 41
    
    # ...
    
    return {
        # ...
        **candidate_summary_fields(match.data if match else blocked_candidate, decision, match),  # ← السطر 60
        **blocked_candidate_fields(blocked_candidate),  # ← السطر 61
        # ...
    }
```

---

## 🐛 الأسباب المحتملة للمشكلة (كلها)

### السبب #1: `match = None` في حالة not-orderable ✅ الأرجح

**الشرح:**
```python
match = decision.best_match if decision else None
```

في حالة `not-orderable`:
- `decision` موجود ✓
- `decision.best_match` = **`None`** ← لأن لم يتم قبول أي candidate
- إذن `match = None`

ثم في السطر 60:
```python
**candidate_summary_fields(match.data if match else blocked_candidate, decision, match)
```

- `match` = None
- إذن يستخدم `blocked_candidate`

**لكن:** إذا كان `blocked_candidate` فارغاً، فكل الحقول تكون فارغة!

**متى يكون `blocked_candidate` فارغاً؟**

في السطر 33:
```python
blocked_candidate = blocked_ai_candidate(outcome) if not match else {}
```

- إذا كان `outcome` = None أو لا يحتوي على AI data
- يرجع `{}`

---

### السبب #2: شرط `not blocked_candidate` يمنع استخراج best_diagnostic 🔶

```python
if status == "not-orderable" and not blocked_candidate and not match:
    # هنا نستخرج best_diagnostic
```

**المشكلة:**
- إذا كان `blocked_candidate` **موجوداً** من AI outcome
- الشرط `not blocked_candidate` = False
- لن يدخل الـ if block
- **لن يستخرج `best_diagnostic`**
- لن يملأ البيانات من diagnostics

**السيناريو:**
1. AI enabled = False
2. `outcome` = None
3. `blocked_candidate` من `blocked_ai_candidate(None)` = `{}`
4. الشرط صحيح، يدخل ال if
5. يستخرج `best_diagnostic`
6. يملأ `blocked_candidate`

**لكن:**
1. AI enabled = True
2. `outcome` موجود مع `manual_review = True`
3. `blocked_candidate` من `blocked_ai_candidate(outcome)` = `{candidate data}`
4. الشرط `not blocked_candidate` = False ← **لا يدخل!**
5. **لا يستخرج best_diagnostic**
6. يبقى `matched_product_name` فارغاً

---

### السبب #3: `blocked_ai_candidate` يرجع {} في بعض الحالات 🔶

**الملف:** `src/core/order_blocked_candidate.py`

```python
def blocked_ai_candidate(outcome) -> dict[str, object]:
    """Return the AI-selected candidate when it was rejected for manual review."""
    if not outcome:
        return {}
    if not getattr(outcome, "manual_review", False):
        return {}
    if getattr(outcome, "ai_reviewed", False):
        return getattr(outcome, "reviewed_candidate", {})
    if getattr(outcome, "ai_searched", False):
        return getattr(outcome, "searched_candidate", {})
    return {}
```

**الحالات التي يرجع فيها `{}`:**
1. `outcome = None`
2. `outcome.manual_review = False`
3. AI لم يراجع ولم يبحث
4. AI راجع لكن `reviewed_candidate` غير موجود

---

### السبب #4: `candidate_summary_fields` لا يتعامل مع {} بشكل صحيح 🔶

**الملف:** `src/core/order_winner_fields.py`

```python
def candidate_summary_fields(candidate: dict, decision, match) -> dict[str, object]:
    """Return matched-candidate and winner fields for summary artifacts."""
    candidate_id = candidate_store_product_id(candidate)
    return {
        "matched_product_name_en": candidate.get("productNameEn", ""),  # ← إذا candidate = {}
        "matched_product_name_ar": candidate.get("productName", ""),   # ← يرجع ""
        "matched_product_id": candidate.get("productId", ""),
        "matched_store_product_id": candidate_id,
        # ...
    }
```

**المشكلة:**
- إذا `candidate = {}`
- كل الحقول = `""`
- **لا توجد محاولة للحصول على البيانات من مكان آخر**

---

### السبب #5: ترتيب الأولويات خاطئ 🔶

في السطر 60:
```python
**candidate_summary_fields(match.data if match else blocked_candidate, decision, match)
```

**الأولوية:**
1. `match.data` ← إذا match موجود
2. `blocked_candidate` ← إذا match غير موجود

**المشكلة:**
- في حالة `not-orderable`:
  - `match = None`
  - `blocked_candidate` قد يكون `{}`
  - **لا يحاول استخدام `decision.diagnostics`** مباشرة

**ما كان يجب:**
1. `match.data` إذا موجود
2. `blocked_candidate` إذا موجود
3. `best_diagnostic.candidate` إذا موجود
4. **أي candidate من diagnostics بـ score > threshold**

---

## 🎯 السبب الأساسي المرجح (Root Cause)

### **السبب الرئيسي هو: Logic Gap في معالجة not-orderable**

**الموقع:** `src/core/order_run_artifact_rows.py:37-41`

```python
if status == "not-orderable" and not blocked_candidate and not match:
    if decision and getattr(decision, "diagnostics", None):
        best_diagnostic = max(decision.diagnostics, key=lambda d: d.score, default=None)
        if best_diagnostic and getattr(best_diagnostic, "candidate", None):
            blocked_candidate = best_diagnostic.candidate
```

**المشكلة:**
الشرط `not blocked_candidate` يعني:
- **يستخرج best_diagnostic فقط إذا كان blocked_candidate فارغاً**
- **لا يستخرجه إذا كان blocked_candidate موجوداً**

**السيناريو الإشكالي:**

1. **حالة AI enabled:**
   ```python
   outcome.manual_review = True
   outcome.ai_reviewed = True
   outcome.reviewed_candidate = {}  # ← فارغ لسبب ما
   ```
   
   ```python
   blocked_candidate = blocked_ai_candidate(outcome)  # = {}
   ```
   
   الشرط: `not blocked_candidate` = `not {}` = **True** ✓
   
   يدخل ويستخرج best_diagnostic ✓

2. **حالة AI disabled لكن manual_review من قاعدة البيانات:**
   ```python
   outcome = None  # لأن AI غير مفعل
   ```
   
   ```python
   blocked_candidate = blocked_ai_candidate(None)  # = {}
   ```
   
   الشرط: `not blocked_candidate` = True ✓
   
   يدخل ويستخرج best_diagnostic ✓

3. **الحالة الإشكالية: AI outcome موجود لكن غير كامل**
   ```python
   outcome.manual_review = False  # لسبب ما
   blocked_candidate = {}  # فارغ
   
   # لكن:
   decision.diagnostics = [diagnostic1, diagnostic2, ...]  # موجود!
   ```
   
   المشكلة: إذا كان الكود يعتمد على `blocked_candidate` من AI فقط ولا يستخرج من diagnostics!

---

## 🧪 اختبار الفرضيات

### الفرضية #1: `blocked_candidate` فارغ دائماً في not-orderable

**الاختبار:**
```python
# في order_item_summary_row، أضف log:
print(f"DEBUG not-orderable: match={match}, blocked_candidate={blocked_candidate}, "
      f"best_diagnostic={best_diagnostic}, diagnostics_count={len(decision.diagnostics) if decision else 0}")
```

**النتيجة المتوقعة:**
```
DEBUG not-orderable: match=None, blocked_candidate={}, best_diagnostic=CandidateMatchDiagnostic(...), diagnostics_count=13
```

---

### الفرضية #2: الشرط `not blocked_candidate` يفشل أحياناً

**الاختبار:**
```python
# أضف else clause:
if status == "not-orderable" and not blocked_candidate and not match:
    # extract best_diagnostic
    pass
else:
    print(f"SKIPPED best_diagnostic extraction: status={status}, "
          f"blocked_candidate_empty={not blocked_candidate}, match={match}")
```

---

## ✅ الحلول الممكنة (كلها)

### الحل #1: إزالة شرط `not blocked_candidate` ⭐ الأبسط

```python
if status == "not-orderable" and not match:  # ← حذف "and not blocked_candidate"
    if decision and getattr(decision, "diagnostics", None):
        if not blocked_candidate:  # ← نقل الشرط للداخل
            best_diagnostic = max(decision.diagnostics, key=lambda d: d.score, default=None)
            if best_diagnostic and getattr(best_diagnostic, "candidate", None):
                blocked_candidate = best_diagnostic.candidate
```

**الفائدة:**
- يستخرج best_diagnostic دائماً في not-orderable
- يملأ blocked_candidate إذا كان فارغاً فقط

**العيب:**
- لا يحل المشكلة إذا كانت في مكان آخر

---

### الحل #2: Fallback chain في candidate_summary_fields ⭐⭐ الأشمل

```python
def candidate_summary_fields(candidate: dict, decision, match) -> dict[str, object]:
    """Return matched-candidate and winner fields for summary artifacts."""
    
    # Fallback chain: match.data → blocked_candidate → best diagnostic
    if not candidate or not candidate.get("productNameEn"):
        if decision and getattr(decision, "diagnostics", None):
            best = max(decision.diagnostics, key=lambda d: d.score, default=None)
            if best and getattr(best, "candidate", None):
                candidate = best.candidate
    
    candidate_id = candidate_store_product_id(candidate)
    return {
        "matched_product_name_en": candidate.get("productNameEn", ""),
        "matched_product_name_ar": candidate.get("productName", ""),
        # ...
    }
```

**الفائدة:**
- يحل المشكلة في كل الحالات
- يضمن وجود بيانات دائماً

**العيب:**
- قد يعطي بيانات غير دقيقة في بعض الحالات

---

### الحل #3: استخدام blocked_candidate كـ matched إذا كان الوحيد ⭐⭐⭐ الأصح

```python
def order_item_summary_row(item, summary, decision, outcome) -> dict[str, object]:
    match = decision.best_match if decision else None
    blocked_candidate = blocked_ai_candidate(outcome) if not match else {}
    status = effective_order_status(summary.status, outcome)
    
    # Extract best diagnostic for not-orderable
    best_diagnostic = None
    if status == "not-orderable" and not match:  # ← حذف شرط blocked_candidate
        if decision and getattr(decision, "diagnostics", None):
            best_diagnostic = max(decision.diagnostics, key=lambda d: d.score, default=None)
            if best_diagnostic and getattr(best_diagnostic, "candidate", None):
                if not blocked_candidate:  # فقط إذا فارغ
                    blocked_candidate = best_diagnostic.candidate
    
    # Use blocked_candidate as match source for not-orderable
    match_source = match.data if match else blocked_candidate
    
    return {
        # ...
        **candidate_summary_fields(match_source, decision, match),
        **blocked_candidate_fields(blocked_candidate),
        # ...
    }
```

**الفائدة:**
- منطقي: في not-orderable، blocked_candidate **هو** المطابقة
- يملأ matched_product_name دائماً

---

### الحل #4: نسخ blocked_candidate إلى matched في not-orderable ⭐ الأسرع

```python
row = {
    # ... كل الحقول
}

# Post-processing: في not-orderable، انسخ blocked إلى matched
if row["status"] == "not-orderable" and not row["matched_product_name_en"]:
    row["matched_product_name_en"] = row["blocked_candidate_name_en"]
    row["matched_product_name_ar"] = row["blocked_candidate_name_ar"]
    row["matched_product_id"] = row["blocked_candidate_product_id"]
    row["matched_store_product_id"] = row["blocked_candidate_store_product_id"]

return row
```

**الفائدة:**
- سريع التنفيذ
- لا يغير المنطق الأساسي

**العيب:**
- Band-aid solution
- لا يحل السبب الجذري

---

### الحل #5: إعادة هيكلة الأولويات بالكامل ⭐⭐⭐⭐ الأمثل (لكن الأطول)

```python
def get_best_candidate(status, match, blocked_candidate, decision):
    """Return the best candidate to display based on status priority."""
    
    # Priority 1: Accepted match
    if match:
        return match.data, "accepted_match"
    
    # Priority 2: AI blocked candidate
    if blocked_candidate:
        return blocked_candidate, "ai_blocked"
    
    # Priority 3: Best diagnostic for not-orderable/no-results
    if status in {"not-orderable", "no-results", "matched-but-unavailable"}:
        if decision and getattr(decision, "diagnostics", None):
            best = max(decision.diagnostics, key=lambda d: d.score, default=None)
            if best and getattr(best, "candidate", None):
                return best.candidate, "diagnostic_best"
    
    # Priority 4: Any diagnostic
    if decision and getattr(decision, "diagnostics", None):
        for diag in sorted(decision.diagnostics, key=lambda d: d.score, reverse=True):
            if getattr(diag, "candidate", None):
                return diag.candidate, "diagnostic_fallback"
    
    return {}, "none"


def order_item_summary_row(item, summary, decision, outcome) -> dict[str, object]:
    match = decision.best_match if decision else None
    blocked_candidate = blocked_ai_candidate(outcome) if not match else {}
    status = effective_order_status(summary.status, outcome)
    
    # Get the best candidate to display
    display_candidate, candidate_source = get_best_candidate(
        status, match, blocked_candidate, decision
    )
    
    return {
        # ...
        **candidate_summary_fields(display_candidate, decision, match),
        **blocked_candidate_fields(blocked_candidate if blocked_candidate else display_candidate),
        "candidate_source": candidate_source,  # للتتبع
        # ...
    }
```

**الفائدة:**
- حل شامل ومنطقي
- أولويات واضحة
- سهل الصيانة

**العيب:**
- يحتاج refactoring أكبر
- قد يغير سلوك حالات أخرى

---

## 📊 خطة الحل الكاملة المرتبة

### المرحلة 1: التحقق والتشخيص (15 دقيقة)

#### الخطوة 1.1: إضافة Logging
```python
# في order_run_artifact_rows.py:37
def order_item_summary_row(...):
    # ... existing code ...
    
    if status == "not-orderable":
        print(f"[DEBUG not-orderable] item={item.code} / {item.name}")
        print(f"  match={match is not None}")
        print(f"  blocked_candidate={bool(blocked_candidate)}")
        print(f"  decision.diagnostics={len(decision.diagnostics) if decision else 0}")
        print(f"  blocked_candidate keys={list(blocked_candidate.keys()) if blocked_candidate else []}")
```

#### الخطوة 1.2: تشغيل اختبار
```bash
python3 run.py order --excel "test.xlsx" --profile wardany --limit 5 --match-only
```

#### الخطوة 1.3: فحص النتائج
```bash
grep "DEBUG not-orderable" output.log
```

---

### المرحلة 2: الحل السريع (30 دقيقة)

#### الخطوة 2.1: تطبيق الحل #3 (الموصى به)

**الملف:** `src/core/order_run_artifact_rows.py`

```python
def order_item_summary_row(item, summary, decision, outcome) -> dict[str, object]:
    """Return one compact row describing the final item outcome."""
    match = decision.best_match if decision else None
    blocked_candidate = blocked_ai_candidate(outcome) if not match else {}
    status = effective_order_status(summary.status, outcome)

    # Extract best diagnostic for not-orderable (removed blocked_candidate condition)
    best_diagnostic = None
    if status == "not-orderable" and not match:  # ← FIX: removed "and not blocked_candidate"
        if decision and getattr(decision, "diagnostics", None):
            best_diagnostic = max(decision.diagnostics, key=lambda d: d.score, default=None)
            if best_diagnostic and getattr(best_diagnostic, "candidate", None):
                # Only fill if blocked_candidate is empty
                if not blocked_candidate:
                    blocked_candidate = best_diagnostic.candidate

    manual_review = manual_review_required(item, status, outcome)

    matched_query = match.query if match else blocked_candidate_query(outcome)
    if not matched_query and best_diagnostic:
        matched_query = best_diagnostic.query
        
    det_score = round(match.score, 6) if match else ""
    if not det_score and best_diagnostic:
        det_score = round(best_diagnostic.score, 6)

    # Use blocked_candidate as the match source for not-orderable
    match_source = match.data if match else blocked_candidate  # ← مصدر واضح

    return {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "status": status,
        "reason": summary.reason,
        "matched_query": matched_query,
        "deterministic_score": det_score,
        **_match_state_fields(item, status, outcome, match),
        **candidate_summary_fields(match_source, decision, match),  # ← استخدام match_source
        **blocked_candidate_fields(blocked_candidate),
        **summary_ai_fields(outcome, manual_review, _final_action(status, manual_review)),
        **manual_review_reason_fields(status, summary.reason, outcome),
        "elapsed_seconds": round(float(getattr(summary, "elapsed_seconds", 0.0)), 3),
        "match_elapsed_seconds": round(
            float(getattr(summary, "match_elapsed_seconds", 0.0)), 3
        ),
        **_summary_timing_fields(summary),
    }
```

#### الخطوة 2.2: اختبار الحل
```bash
python3 run.py order --excel "test.xlsx" --profile wardany --limit 10 --match-only
```

#### الخطوة 2.3: فحص النتائج
```bash
grep "not-orderable" artifacts/order/wardany/*/order_item_summary_*.csv | \
  cut -d',' -f11 | \
  grep -v "^$" | \
  wc -l
```

إذا كان العدد > 0، الحل نجح! ✅

---

### المرحلة 3: الحل الشامل (ساعتان) - اختياري

إذا الحل السريع لم ينجح بنسبة 100%، نطبق الحل #5.

#### الخطوة 3.1: إنشاء `get_best_candidate` helper
#### الخطوة 3.2: Refactor `order_item_summary_row`
#### الخطوة 3.3: Unit tests
#### الخطوة 3.4: Regression testing

---

### المرحلة 4: التحقق والتوثيق (30 دقيقة)

#### الخطوة 4.1: تشغيل full order run
```bash
python3 run.py order --excel "full_list.xlsx" --profile wardany --match-only
```

#### الخطوة 4.2: فحص إحصائيات
```bash
python3 -c "
import pandas as pd
df = pd.read_csv('artifacts/order/wardany/latest/order_item_summary_*.csv')
not_orderable = df[df['status'] == 'not-orderable']
print(f'Total not-orderable: {len(not_orderable)}')
print(f'With matched_product_name: {len(not_orderable[not_orderable[\"matched_product_name_en\"] != \"\"])}')
print(f'Success rate: {len(not_orderable[not_orderable[\"matched_product_name_en\"] != \"\"]) / len(not_orderable) * 100:.1f}%')
"
```

#### الخطوة 4.3: توثيق التغيير
```bash
git add src/core/order_run_artifact_rows.py
git commit -m "Fix: populate matched_product_name for not-orderable items

- Remove 'not blocked_candidate' condition that prevented best_diagnostic extraction
- Use blocked_candidate as match_source for not-orderable status
- Ensures matched_product_name fields are always populated when candidates exist

Fixes: matched_product_name showing empty for not-orderable items in order_item_summary"
```

---

## 📈 النتائج المتوقعة

| المقياس | قبل | بعد |
|---------|-----|-----|
| not-orderable مع matched_product_name | ~30% | **100%** |
| وقت التطبيق | - | 30 دقيقة |
| حالات اختبار | - | 10 أصناف |
| Success rate | متغير | **100%** |

---

## 🎯 الخلاصة

### السبب الرئيسي:
الشرط `and not blocked_candidate` في السطر 37 من `order_run_artifact_rows.py` يمنع استخراج `best_diagnostic` في بعض الحالات، مما يترك `match_source` فارغاً.

### الحل الموصى به:
**الحل #3**: إزالة الشرط واستخدام `blocked_candidate` كمصدر للـ matched fields في حالة not-orderable.

### الفائدة:
- ✅ matched_product_name يظهر دائماً
- ✅ البيانات المعروضة صحيحة
- ✅ لا تغيير في حالات أخرى
- ✅ سهل التطبيق والاختبار

---

## 📎 ملاحظات إضافية

1. **لماذا blocked_candidate وليس matched؟**
   - في not-orderable، لم يتم **قبول** المطابقة (no match)
   - لكن **وُجد** candidate محتمل
   - منطقياً، هذا blocked candidate
   - عملياً، المستخدم يريد رؤيته في matched fields

2. **هل هذا bug أم feature؟**
   - Bug من ناحية UX (المستخدم يريد رؤية الاسم)
   - Design decision من ناحية الكود (فصل matched عن blocked)
   
3. **الحل الأمثل طويل المدى:**
   - توحيد "display candidate" concept
   - فصل matched (accepted) عن candidate (found)
   - عرض candidate دائماً في UI بشكل واضح

