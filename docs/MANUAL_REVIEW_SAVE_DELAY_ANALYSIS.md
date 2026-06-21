# تحليل التأخر في حفظ Manual Review

## المشكلة: بطء حفظ الأصناف في قاعدة البيانات

عند الضغط على زر "Save Manual Review Decisions" في واجهة Streamlit، يحدث تأخر ملحوظ قبل تأكيد الحفظ.

---

## السبب الرئيسي: حلقة UPSERT المتسلسلة

### الكود الحالي:
```python
def save_manual_review_rows(rows: list[dict], run_id: str) -> int:
    store = ManualReviewStore(store_path)
    decisions = manual_review_decisions_from_rows(rows, run_id)
    for decision in decisions:
        store.upsert(decision)  # ⚠️ استعلام منفصل لكل صنف
    return len(decisions)
```

### المشكلة:

#### 1. **استعلام منفصل لكل صنف** 🐌
```python
for decision in decisions:
    store.upsert(decision)  # كل صنف = 1 استعلام SQL
```

- إذا كان لديك **50 صنفاً**، يُنفذ **50 استعلام SQL منفصل**
- كل استعلام يحتاج:
  - فتح اتصال بقاعدة البيانات
  - إرسال البيانات
  - تنفيذ UPSERT
  - commit
  - إغلاق الاتصال
  - **Network latency** للـ CockroachDB Cloud

#### 2. **Network Latency مع CockroachDB Cloud** 🌐
```python
DEFAULT_HOST = "mahrousdb-27867.j77.aws-eu-central-1.cockroachlabs.cloud"
```

- قاعدة البيانات موجودة على **AWS EU Central (Frankfurt)**
- كل استعلام يحتاج رحلة ذهاب وعودة (round-trip):
  - مصر → ألمانيا: ~80-120ms
  - المعالجة: ~10-30ms
  - ألمانيا → مصر: ~80-120ms
  - **إجمالي: ~170-270ms لكل صنف**

#### 3. **Transaction Overhead** 💾
```python
def execute_update(self, query: str, params: tuple = ()) -> int:
    with self.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        affected = cur.rowcount
        conn.commit()  # ⚠️ commit منفصل لكل صنف
        cur.close()
        return affected
```

كل `upsert` له:
- Transaction جديدة
- Commit منفصل
- Lock على الجدول

---

## الحساب الرياضي

### مثال: حفظ 50 صنف

| العنصر | الوقت لكل صنف | الإجمالي |
|--------|--------------|---------|
| Network latency | 200ms | 10,000ms (10s) |
| Query execution | 30ms | 1,500ms (1.5s) |
| Connection overhead | 20ms | 1,000ms (1s) |
| Transaction commit | 50ms | 2,500ms (2.5s) |
| **الإجمالي** | **~300ms** | **~15 ثانية** ⏱️ |

---

## التفاصيل الفنية

### 1. مسار الحفظ الكامل

```
[Streamlit UI]
    ↓
[save_manual_review_rows]
    ↓
[manual_review_decisions_from_rows]  // تحويل الصفوف إلى objects
    ↓
[for loop: store.upsert(decision)]   // ⚠️ BOTTLENECK
    ↓
[ManualReviewStore.upsert]
    ↓
[DatabaseManager.execute_update]
    ↓
[psycopg2: connection → execute → commit]
    ↓
[CockroachDB Cloud في Frankfurt]
```

### 2. استعلام UPSERT الفردي

```sql
insert into manual_review_decisions
(item_code_key, item_name_key, item_code, item_name, approved, 
 manual_decision, correct_store_product_id, correct_product_name, 
 correct_product_name_ar, correct_query, run_id)
values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
on conflict(item_code_key, item_name_key) do update set
approved=excluded.approved,
manual_decision=excluded.manual_decision,
correct_store_product_id=excluded.correct_store_product_id,
correct_product_name=excluded.correct_product_name,
correct_product_name_ar=excluded.correct_product_name_ar,
correct_query=excluded.correct_query,
run_id=excluded.run_id,
updated_at=current_timestamp
```

هذا يُنفذ **مرة واحدة لكل صنف** 🔁

### 3. Connection Pool Behavior

```python
self.connection_pool = pool.SimpleConnectionPool(
    1,
    5,  # Min 1, Max 5 connections
    ...
)
```

- حتى مع Connection Pool، كل `upsert` يحتاج:
  - `getconn()` - أخذ connection من pool
  - `execute()` - تنفيذ الاستعلام
  - `commit()` - حفظ التغييرات
  - `putconn()` - إرجاع connection للـ pool

---

## الحلول المقترحة

### الحل 1: Batch UPSERT ⚡ (الأفضل)

```python
def save_manual_review_rows(rows: list[dict], run_id: str) -> int:
    store = ManualReviewStore(store_path)
    decisions = manual_review_decisions_from_rows(rows, run_id)
    
    # إرسال كل الأصناف في استعلام واحد
    store.upsert_batch(decisions)  # ✅ 1 استعلام فقط
    return len(decisions)
```

**الفائدة:**
- من **50 استعلام** → **1 استعلام**
- من **15 ثانية** → **~500ms** ⚡
- توفير **96% من الوقت**

---

### الحل 2: Async Database Calls 🔄

```python
import asyncio
import asyncpg

async def upsert_many_async(decisions):
    async with db_pool.acquire() as conn:
        await conn.executemany(UPSERT_DECISION, values)
```

**الفائدة:**
- الاستعلامات تُنفذ بالتوازي
- تقليل الوقت الكلي بنسبة 60-70%

---

### الحل 3: Transaction Batching 💾

```python
def upsert_batch(self, decisions):
    with self.db.get_connection() as conn:
        cur = conn.cursor()
        for decision in decisions:
            cur.execute(UPSERT_DECISION, values)
        conn.commit()  # ✅ commit واحد في النهاية
        cur.close()
```

**الفائدة:**
- تقليل Transaction overhead
- من **50 commit** → **1 commit**

---

### الحل 4: Local Caching + Background Sync 📦

```python
# حفظ محلي فوري
local_cache.save(decisions)
st.success("Saved locally!")

# مزامنة في الخلفية
background_thread.sync_to_cloud(decisions)
```

**الفائدة:**
- المستخدم يشوف النتيجة فوراً
- المزامنة تحصل في الخلفية

---

## التوصية النهائية

**استخدم Batch UPSERT** لأنه:
1. ✅ الأسرع (توفير 96%)
2. ✅ الأبسط في التنفيذ
3. ✅ لا يحتاج تغيير معماري كبير
4. ✅ يدعم CockroachDB بشكل كامل

### كود التنفيذ المقترح:

```python
def upsert_batch(self, decisions: list[ManualReviewDecision]) -> None:
    """Batch insert/update multiple decisions in one transaction."""
    if not decisions:
        return
    
    values = [
        _decision_values(*hint_key(d.item_code, d.item_name), d) 
        for d in decisions
    ]
    
    # استخدام executemany بدل execute
    with self.db.get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(UPSERT_DECISION, values)
        conn.commit()
        cur.close()
```

---

## الخلاصة

| المقياس | قبل | بعد |
|---------|-----|-----|
| عدد الاستعلامات | 50 | 1 |
| الوقت الكلي | ~15s | ~0.5s |
| Network calls | 50 | 1 |
| Commits | 50 | 1 |
| تحسين السرعة | - | **96%** ⚡ |

**السبب الرئيسي للبطء:** الحلقة المتسلسلة (`for loop`) مع استعلام منفصل لكل صنف + Network latency لـ CockroachDB Cloud.

**الحل الأمثل:** Batch UPSERT باستخدام `executemany` لإرسال كل الأصناف في استعلام واحد.
