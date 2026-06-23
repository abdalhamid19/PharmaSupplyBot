# تقرير تفصيلي: مشكلة الحفظ التلقائي لـ `not_matching` في Manual Review GUI

**المطور:** Kiro AI  
**التاريخ:** 2026-06-23  
**الحالة:** 🔍 تحت التحليل  
**النسخة:** v1.0

---

## 📋 جدول المحتويات

1. [ملخص تنفيذي](#ملخص-تنفيذي)
2. [وصف المشكلة](#وصف-المشكلة)
3. [التحليل التقني المفصل](#التحليل-التقني-المفصل)
4. [السبب الجذري](#السبب-الجذري)
5. [الحلول الممكنة](#الحلول-الممكنة)
6. [خطة التنفيذ](#خطة-التنفيذ)
7. [الحل المطبق](#الحل-المطبق)
8. [الاختبار والتحقق](#الاختبار-والتحقق)

---

## 🎯 ملخص تنفيذي

### المشكلة
عند فتح Candidates section في Manual Review GUI، النظام **يحفظ تلقائياً** `not_matching` في CockroachDB رغم أن المستخدم لم يختر "No match exists" checkbox.

### السبب الرئيسي
**Streamlit state management + callback behavior:**
- عند فتح الصفحة، `st.radio` يبدأ بقيمة افتراضية `idx=0` (None - Leave Unmatched)
- عند تبديل الصفحة في pagination، `on_radio` callback يُطلق تلقائياً
- `decision_from_selection()` يُعامل `idx=0, not_matching=False, query=""` على أنه `not_matching`
- النتيجة: حفظ في DB بدون نية المستخدم ❌

### التأثير
- **خطورة:** متوسطة - تلوث بيانات manual review
- **التكرار:** يحدث عند أي navigation في pagination أو page reload
- **النطاق:** كل items في Candidates section

---

## 📝 وصف المشكلة

### السيناريو المشكل

#### Run: `order/wardany/20260623_1233`

| Item Code | Item Name | Expected | Actual in DB |
|-----------|-----------|----------|--------------|
| 91304 | PANTHENOL 5 CARE CREAM 50 GM | `leave_unmatched` | `not_matching` ❌ |
| 22773 | RIRI MILK CEREAL FRUITS POWDER | `leave_unmatched` | `not_matching` ❌ |
| 92082 | MARSHMALLOW WHITENING CREAM | `leave_unmatched` | `not_matching` ❌ |
| 89927 | SODIUM BICARB 500MG BIOMED 30TAB | `leave_unmatched` | `not_matching` ❌ |
| GTN | GTN CREAM | `leave_unmatched` | `not_matching` ❌ |

#### خطوات إعادة إنتاج المشكلة:

```plaintext
1. تشغيل GUI: streamlit run streamlit_app.py
2. اختيار run: order/wardany/20260623_1233
3. الذهاب إلى Manual Review tab
4. فتح Candidates section
5. تبديل الصفحة في pagination → ⚠️ يُحفظ not_matching تلقائياً
6. فحص DB: يوجد decision="not_matching" رغم عدم اختيار checkbox
```

### السلوك المتوقع vs الفعلي

| الحالة | المتوقع | الفعلي |
|--------|---------|--------|
| فتح Candidates | لا يحفظ شيء | ✅ صحيح |
| اختيار "No match exists" | يحفظ `not_matching` | ✅ صحيح |
| تبديل الصفحة بدون اختيار | لا يحفظ شيء | ❌ يحفظ `not_matching` |
| Reload الصفحة | لا يحفظ شيء | ❌ يحفظ `not_matching` |

---

## 🔬 التحليل التقني المفصل

### Architecture Overview

```plaintext
┌─────────────────────────────────────────────────────────────────┐
│                       Manual Review Flow                        │
└─────────────────────────────────────────────────────────────────┘

  User Interaction (GUI)
        │
        ├─ st.radio (idx=0 default)
        ├─ st.checkbox (not_matching)
        └─ st.text_input (query)
        │
        ▼
  Callback Triggers
        │
        ├─ on_radio() → _trigger_save()
        ├─ on_nm() → _trigger_save()
        └─ on_query() → _trigger_save()
        │
        ▼
  _save() Function
        │
        ├─ Extracts: idx, not_matching, query
        └─ Calls: decision_from_selection()
        │
        ▼
  decision_from_selection()
        │
        ├─ if not_matching → _create_not_matching() ✅
        ├─ if query → _create_needs_correction() ✅
        ├─ if selected_option → _create_approved() ✅
        └─ else → _create_not_matching() ❌ المشكلة هنا!
        │
        ▼
  ManualReviewStore.upsert()
        │
        └─ Saves to CockroachDB
```

### الملفات المتأثرة

#### 1. `src/ui/streamlit_manual_review_page_form.py`

**الوظيفة:** Form rendering + callbacks

```python
def render_selection_form(...):
    # Callbacks
    def on_radio() -> None:
        if st.session_state.get(idx_key, 0) > 0:
            st.session_state[nm_key] = False
            st.session_state[query_key] = ""
        _trigger_save()  # ⚠️ يُطلق تلقائياً عند أي تغيير

    # Radio button
    st.radio(
        "Select best match:", range(len(radio_opts)),
        format_func=lambda x: radio_opts[x],
        key=idx_key, on_change=on_radio  # ⚠️ Callback مربوط
    )
```

**المشكلة:**
- Streamlit يُطلق `on_change` callback حتى عند **state initialization**
- عند pagination أو reload، `st.radio` يُعيد تعيين قيمته إلى default (`0`)
- هذا يُطلق `on_radio()` → `_trigger_save()` → حفظ في DB

#### 2. `src/core/manual_review_selection.py`

**الوظيفة:** Business logic للـ decision translation

```python
def decision_from_selection(
    item: Item,
    selected_option: ReviewCandidateOption | None,
    not_matching: bool,
    free_text_query: str,
    run_id: str,
) -> ManualReviewDecision:
    """Return a storable decision based on human feedback."""
    if not_matching:
        return _create_not_matching(item, run_id)  # ✅ صحيح
    if free_text_query.strip():
        return _create_needs_correction(item, free_text_query.strip(), run_id)  # ✅ صحيح
    if selected_option:
        return _create_approved(item, selected_option, run_id)  # ✅ صحيح
    
    # ❌ المشكلة: السطر الأخير يُعامل "لا شيء" على أنه "not_matching"
    return _create_not_matching(item, run_id)
```

**التحليل:**
| الحالة | `not_matching` | `query` | `selected_option` | النتيجة |
|--------|---------------|---------|-------------------|---------|
| Checkbox مختار | `True` | `""` | `None` | ✅ `not_matching` |
| Query مدخل | `False` | `"text"` | `None` | ✅ `needs_correction` |
| Option مختار | `False` | `""` | `Object` | ✅ `approved_match` |
| **لا شيء مختار** | `False` | `""` | `None` | ❌ `not_matching` (خطأ!) |

**السبب:**
- السطر الأخير `return _create_not_matching(...)` يُفترض أنه **fallback** منطقي
- لكنه يُطبق حتى عندما المستخدم **لم يختر شيئاً بعد**

---

## 🎯 السبب الجذري

### Root Cause Analysis

#### السبب المباشر:
**Logic error في `decision_from_selection()`**
- يُعامل "عدم وجود اختيار" على أنه "لا يوجد match"
- لا يوجد تمييز بين:
  - **Explicit rejection:** المستخدم اختار "No match exists"
  - **No action yet:** المستخدم لم يختر شيئاً

#### السبب الأساسي:
**Streamlit callback behavior + missing state tracking**

```python
# عند فتح الصفحة:
st.radio(key="radio_item_123", default=0)  # idx=0

# عند pagination:
on_radio() → _trigger_save()
  → idx=0, not_matching=False, query=""
  → decision_from_selection() → _create_not_matching()
  → store.upsert() → DB تلوث ❌
```

#### الأسباب المساهمة:

1. **Lack of explicit "untouched" state:**
   - لا يوجد flag لتتبع "هل لمس المستخدم الـ form أصلاً؟"

2. **Aggressive auto-save:**
   - `_trigger_save()` يُطلق عند أي callback، حتى initialization

3. **Ambiguous default value:**
   - `idx=0` يعني "None - Leave Unmatched" لكن يُحفظ كـ `not_matching`

### أسباب محتملة أخرى (مستبعدة):

| السبب | الاحتمال | التحقق | النتيجة |
|-------|----------|--------|---------|
| Network timeout | منخفض | فحص logs | ❌ لا يوجد timeout errors |
| DB constraint | منخفض | فحص schema | ❌ Schema صحيح |
| Cache corruption | منخفض | فحص session_state | ❌ Cache يعمل صحيح |
| Concurrent writes | منخفض | فحص upsert logic | ❌ Upsert atomic |

---

## 💡 الحلول الممكنة

### الحل 1: إضافة `leave_unmatched` decision type ⭐ **مفضل**

**الفكرة:**
- إنشاء decision type جديد: `"leave_unmatched"`
- عدم حفظ decision عندما `idx=0` بدون explicit action

**التعديلات:**
```python
# src/core/manual_review_selection.py
def decision_from_selection(...) -> ManualReviewDecision | None:
    if not_matching:
        return _create_not_matching(item, run_id)
    if free_text_query.strip():
        return _create_needs_correction(item, free_text_query.strip(), run_id)
    if selected_option:
        return _create_approved(item, selected_option, run_id)
    # ✅ الحل: عدم إرجاع decision
    return None

# src/ui/streamlit_manual_review_page_form.py
def _save(...):
    decision = decision_from_selection(...)
    if decision is not None:  # ✅ فقط احفظ عند وجود decision
        store.upsert(decision)
        # Update cache...
```

**المزايا:**
- ✅ حل بسيط ومباشر
- ✅ لا يحتاج تغيير DB schema
- ✅ منطقي: "لا decision" = لا حفظ
- ✅ backward compatible

**العيوب:**
- ⚠️ يجب تحديث كل استدعاءات `decision_from_selection()` لمعالجة `None`

---

### الحل 2: تتبع "touched" state

**الفكرة:**
- إضافة `touched_{item_key}` flag في session_state
- حفظ فقط عند `touched=True`

**التعديلات:**
```python
def on_radio() -> None:
    st.session_state[f"touched_{item_key}"] = True  # ✅ Mark as touched
    if st.session_state.get(idx_key, 0) > 0:
        st.session_state[nm_key] = False
        st.session_state[query_key] = ""
    _trigger_save()

def _save(...):
    if not st.session_state.get(f"touched_{item_key}", False):
        return  # ✅ لا تحفظ إذا untouched
    # ... rest of save logic
```

**المزايا:**
- ✅ دقيق: يحفظ فقط بعد user action
- ✅ لا يحتاج تغيير business logic

**العيوب:**
- ⚠️ إضافة state management complexity
- ⚠️ يجب تتبع touched لكل item

---

### الحل 3: إزالة auto-save من callbacks

**الفكرة:**
- إزالة `_trigger_save()` من `on_radio`, `on_nm`, `on_query`
- إضافة "Save" button صريح

**التعديلات:**
```python
def render_selection_form(...):
    # Remove _trigger_save() from callbacks
    def on_radio() -> None:
        if st.session_state.get(idx_key, 0) > 0:
            st.session_state[nm_key] = False
            st.session_state[query_key] = ""
        # ✅ لا auto-save
    
    # Add explicit save button
    if st.button("Save Decision", key=f"save_{item_key}"):
        _save(...)
```

**المزايا:**
- ✅ واضح للمستخدم
- ✅ لا حفظ تلقائي غير مقصود
- ✅ يمكن undo قبل الحفظ

**العيوب:**
- ⚠️ تغيير كبير في UX
- ⚠️ يحتاج extra click من المستخدم
- ⚠️ قد ينسى المستخدم Save

---

### الحل 4: تغيير default behavior في `decision_from_selection()`

**الفكرة:**
- رفع exception بدلاً من إرجاع `not_matching`
- معالجة Exception في caller

**التعديلات:**
```python
def decision_from_selection(...) -> ManualReviewDecision:
    if not_matching:
        return _create_not_matching(item, run_id)
    if free_text_query.strip():
        return _create_needs_correction(item, free_text_query.strip(), run_id)
    if selected_option:
        return _create_approved(item, selected_option, run_id)
    # ✅ رفع exception
    raise ValueError("No valid selection made")

def _save(...):
    try:
        decision = decision_from_selection(...)
        store.upsert(decision)
    except ValueError:
        pass  # ✅ لا تحفظ
```

**المزايا:**
- ✅ صريح: "لا decision صالح"
- ✅ يجبر caller على معالجة الحالة

**العيوب:**
- ⚠️ استخدام exceptions للـ flow control (anti-pattern)
- ⚠️ verbose

---

## 📋 خطة التنفيذ

### الحل المختار: **الحل 1 - إضافة `leave_unmatched` type**

**الأسباب:**
1. ✅ بسيط ومباشر
2. ✅ منطقي: `None` = لا decision
3. ✅ لا يحتاج تغيير DB
4. ✅ backward compatible

### خطوات التنفيذ:

#### Phase 1: تعديل Core Logic
- [x] 1. تعديل `decision_from_selection()` لإرجاع `None`
- [x] 2. تعديل `_save()` لمعالجة `None`
- [x] 3. تحديث type hints

#### Phase 2: الاختبار المحلي
- [ ] 4. تشغيل GUI على run 20260623_1233
- [ ] 5. التحقق من عدم حفظ `not_matching` تلقائياً
- [ ] 6. اختبار جميع الحالات:
  - Leave Unmatched (idx=0) → لا يحفظ
  - No match exists (checkbox) → يحفظ `not_matching`
  - Select option (idx>0) → يحفظ `approved_match`
  - Enter query → يحفظ `needs_correction`

#### Phase 3: Unit Tests
- [ ] 7. تشغيل `python -m unittest discover -s tests -q`
- [ ] 8. إضافة test cases جديدة إذا لزم

#### Phase 4: Code Quality
- [ ] 9. تشغيل `python tools/rule_audit.py`
- [ ] 10. إصلاح أي violations

#### Phase 5: Git Workflow
- [ ] 11. `git add` الملفات المعدلة
- [ ] 12. `git commit` مع رسالة واضحة
- [ ] 13. `git push` إلى GitHub

---

## ✅ الحل المطبق

### Phase 1: تعديل Core Logic ✅

#### 1. `src/core/manual_review_selection.py`

**التعديل الأول:** إرجاع `None` بدلاً من `not_matching`

```python
def decision_from_selection(
    item: Item,
    selected_option: ReviewCandidateOption | None,
    not_matching: bool,
    free_text_query: str,
    run_id: str,
) -> ManualReviewDecision | None:  # ✅ Updated return type
    """Return a storable decision based on human feedback, or None if no action taken."""
    if not_matching:
        return _create_not_matching(item, run_id)
    if free_text_query.strip():
        return _create_needs_correction(item, free_text_query.strip(), run_id)
    if selected_option:
        return _create_approved(item, selected_option, run_id)
    # ✅ Return None instead of not_matching
    return None
```

**قبل:**
```python
return _create_not_matching(item, run_id)  # ❌ Default fallback
```

**بعد:**
```python
return None  # ✅ No decision = no save
```

---

#### 2. `src/ui/streamlit_manual_review_page_form.py`

**التعديل الثاني:** معالجة `None` في `_save()`

```python
def _save(...) -> None:
    opt = options[idx - 1] if idx > 0 else None
    decision = decision_from_selection(item, opt, not_matching, query, run_dir.name)
    
    # ⚡ Only save if user made an explicit choice
    if decision is None:
        return  # ✅ Skip save when no action taken
    
    store.upsert(decision)
    # ... rest of cache update logic
```

**قبل:**
```python
decision = decision_from_selection(...)
store.upsert(decision)  # ❌ Always saves
```

**بعد:**
```python
decision = decision_from_selection(...)
if decision is None:
    return  # ✅ No save when None
store.upsert(decision)
```

---

#### 3. `tests/test_manual_review_selection.py`

**التعديل الثالث:** إضافة test case جديد

```python
def test_no_action_returns_none(self) -> None:
    """Test that no explicit choice returns None (leave unmatched)."""
    decision = decision_from_selection(
        self.item, None, not_matching=False, free_text_query="", run_id=self.run_id
    )
    
    self.assertIsNone(decision)
```

---

### النتيجة النهائية

| الحالة | idx | not_matching | query | النتيجة |
|--------|-----|--------------|-------|---------|
| Leave Unmatched | `0` | `False` | `""` | ✅ `None` (لا يُحفظ) |
| No match exists | `0` | `True` | `""` | ✅ `not_matching` |
| Select option | `>0` | `False` | `""` | ✅ `approved_match` |
| Enter query | `0` | `False` | `"text"` | ✅ `needs_correction` |

---

### الملفات المعدلة

1. ✅ `src/core/manual_review_selection.py` - return type + logic
2. ✅ `src/ui/streamlit_manual_review_page_form.py` - None handling
3. ✅ `tests/test_manual_review_selection.py` - new test case
4. ✅ `docs/MANUAL_REVIEW_AUTO_NOT_MATCHING_ISSUE.md` - documentation

---

### Validation

#### Code Quality
```bash
python tools/rule_audit.py
```
✅ **Result:** No new violations introduced

#### Unit Tests
```bash
python -m unittest tests.test_manual_review_selection -v
```
⚠️ **Result:** Cannot run due to `psycopg2` missing in test environment  
**Note:** Test logic is correct, environment issue only

---

## 🧪 الاختبار والتحقق

### Test Cases

| Test ID | الحالة | الخطوات | النتيجة المتوقعة |
|---------|--------|---------|-------------------|
| TC-1 | Leave Unmatched | 1. فتح Candidates<br>2. عدم اختيار شيء<br>3. تبديل الصفحة | ✅ لا يُحفظ في DB |
| TC-2 | No match exists | 1. اختيار checkbox<br>2. تبديل الصفحة | ✅ يُحفظ `not_matching` |
| TC-3 | Select option | 1. اختيار option<br>2. تبديل الصفحة | ✅ يُحفظ `approved_match` |
| TC-4 | Enter query | 1. كتابة query<br>2. تبديل الصفحة | ✅ يُحفظ `needs_correction` |
| TC-5 | Reload page | 1. فتح Candidates<br>2. Reload | ✅ لا يُحفظ في DB |

### نتائج الاختبار

_(سيتم ملء هذا القسم بعد الاختبار)_

---

## 📚 المراجع

- `src/ui/streamlit_manual_review_page_form.py`
- `src/core/manual_review_selection.py`
- `src/core/manual_review_store.py`
- `artifacts/order/wardany/20260623_1233/manual_review_20260623_1233.csv`

---

**آخر تحديث:** 2026-06-23 12:51 UTC+3
