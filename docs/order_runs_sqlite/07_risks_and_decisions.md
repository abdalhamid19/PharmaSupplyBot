# 07 — المخاطر والقرارات المعمارية

## المخاطر الحقيقية، مرتبة بالخطورة

### 1. 🔴 هوية المخزن الخاطئة — الخطر الأكبر

`_store_identity()` في `src/tawreed/store/tawreed_store_selection.py:55`:

```python
def _store_identity(index, store) -> str:
    for key in ("storeProductId", "productStoreId", "storeId", "supplierId", "id"):
        value = str(store.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    return f"storeName:{store_name(store)}:{index}"
```

`storeProductId` أولاً. **هذا صحيح تماماً لغرضه الأصلي** — منع اختيار
نفس سطر المنتج-في-المخزن مرتين داخل نفس الحلقة. لكنه كارثي كهوية مخزن:

- `storeProductId` = 2902379 هو معرّف «كال ماج في مخزن العاصمة»
- نفس مخزن العاصمة له `storeProductId` مختلف لكل منتج يبيعه
- إعادة استخدامه في جدول `stores` سيُنتج صفاً جديداً لكل (منتج، مخزن)
- بعد 300 صنف × 15 مخزناً سيحتوي جدول «المخازن» على 4500 صف بدل ~30

**النتيجة**: كل استعلام يجمّع بالمخزن (استعلامات 5، 6، 12 في
`05_queries_and_use_cases.md`) سيُرجع نتائج بلا معنى، وسيبدو كل شيء طبيعياً
لأن الأرقام موجودة.

**الحل**: دالة منفصلة في `src/core/ordering/store_identity.py`:

```python
STORE_ID_KEYS = ("storeId", "supplierId", "warehouseId", "branchId")

def store_identity_key(store: dict) -> str:
    """Return a stable store-level identity, never a product-level id."""
    for key in STORE_ID_KEYS:
        value = _clean(store.get(key))
        if value:
            return f"{key}:{value}"
    name = store_name(store)
    return f"storeName:{name}" if name else ""
```

`storeProductId` مُستثنى صراحةً. الرجوع للاسم بلا `index` (بخلاف الأصل)
لأن الفهرس داخل نافذة المخازن يتغير بين runs.

**لا تعدّل `_store_identity()` الأصلية** — تعديلها يغيّر سلوك اختيار
المخازن، وهو خارج نطاق هذه الميزة تماماً. دالتان لغرضين مختلفين.

**احتياط**: يجب فحص حمولة `get_store_details` الفعلية للتأكد من وجود
`storeId`. الحمولة الموجودة في `api_raw_candidate_json` هي حمولة **البحث**
لا حمولة تفاصيل المخازن، وهي تحتوي `storeName` و`companyName` فقط بلا
`storeId`. إن غاب `storeId` من حمولة المخازن أيضاً، فالاسم هو الهوية
الوحيدة المتاحة — وهذا مقبول لكنه يجعل تغيير اسم المخزن في Tawreed يظهر
كمخزن جديد. سجّل ذلك ولا تخفه.

### 2. 🔴 تسمية الأسعار المضلِّلة

من `src/core/ordering/order_winner_fields.py:34-35`:

```python
"winner_sale_price":     public_price,   # ← من retailPrice/publicPrice
"winner_Purchase_Price": sales_price,    # ← من salePrice/salesPrice
```

الاسم `sale_price` يحمل سعر **الجمهور**، والاسم `Purchase_Price` يحمل
`salePrice`. مقلوب المعنى الحدسي.

بالأرقام من run حقيقي: `retailPrice: 147.0`, `salePrice: 116.13`,
`discountPercent: 21.0`. والتحقق: `(147 − 116.13) / 147 = 21%` ✅ — فما
تدفعه فعلاً هو 116.13 وهو `salePrice`.

كذلك `winner_Purchase_Price` بحرف كبير في المنتصف يخالف `snake_case`
المطلوب في `docs/project_guidelines.md:41`.

**الحل**: أسماء واضحة في قاعدة البيانات وتوثيق المقابلة:

| عمود القاعدة | مصدر Tawreed | العمود القديم في CSV |
|---|---|---|
| `public_price` | `retailPrice` | `winner_sale_price` |
| `purchase_price` | `salePrice` | `winner_Purchase_Price` |

**لا تُصحَّح أسماء أعمدة CSV** في هذه الميزة — تصحيحها يكسر
`docs/order_summary_columns_audit_20260710/` وكل قارئ خارجي. سجّلها في
`docs/PROJECT_MAP.md` كدين تقني منفصل.

### 3. 🟠 نمو حجم القاعدة

المخطط الكامل ~0.6 MB لكل run بـ 300 صنف. 500 run ≈ 300 MB. مقبول، لكن
مع `run_candidates` مُفعَّلاً سيتضاعف ثلاث مرات (`match_only_summary` وحده
133 KB لـ run صغير).

**الحل**:
- `store_candidates: false` افتراضياً
- عدم تخزين `api_raw_candidate_json` أبداً
- عدم تخزين 11 عمود توقيت
- سياسة حذف موثقة: `DELETE FROM runs WHERE started_at < ?` + `VACUUM`

### 4. 🟠 القفل عند العمال المتوازين

`item_workers > 1` → عمليات `spawn` تكتب في نفس الملف. بلا الإعدادات
الصحيحة ستظهر `sqlite3.OperationalError: database is locked` بشكل متقطع
— وهو أسوأ نوع من الأخطاء لأنه لا يظهر في الاختبارات ذات العامل الواحد.

**الحل**: WAL (موجود) + `busy_timeout=30000` + `BEGIN IMMEDIATE` + معاملة
قصيرة لكل عنصر + `try/except` يمنع الانتشار. مع ذلك، **يجب اختبار
`--item-workers 4` صراحةً** قبل اعتبار المرحلة 3 مكتملة.

### 5. 🟡 تسرّب المخازن بين الأصناف

`bot.last_store_rows` حالة قابلة للتغيير على كائن مشترك. إن لم تُصفَّر
قبل كل عنصر، ستُنسَب مخازن الصنف N إلى الصنف N+1.

هذا الخطأ **صامت تماماً** — البيانات ستبدو معقولة وتكون خاطئة. أخطر من
انفجار واضح.

**الحل**: التصفير في `_reset_last_item_state()` (`tawreed_bot_core.py:73`)
الذي يُستدعى قبل كل عنصر أصلاً، **مع اختبار مخصص** لهذه الحالة تحديداً.

المشروع يعتمد هذا النمط بالفعل (`last_selected_store_name`,
`last_match_decision`) فهذا اتساق لا اختراع.

### 6. 🟡 حالات المطابقة الفاشلة

عندما `status = 'no-results'` لا يوجد `winner_store_product_id` ولا
`store_rows`. المخطط يعالجها بـ `NULL` في الأعمدة الاختيارية.

لكن هذا يعني أن `COUNT(*) FROM run_item_stores` لا يساوي عدد الأصناف.
كل استعلام يفترض وجود صف مخزن لكل صنف يجب أن يستخدم `LEFT JOIN` — وهذا
مطبَّق في `v_run_winners`.

الأصناف بلا نتائج ليست عيباً في البيانات، بل معلومة بذاتها (استعلام 9).

### 7. 🟡 `run_id` بدقة الدقيقة

`RUN_ID_FORMAT = "%Y%m%d_%H%M"` (`artifact_run.py:13`). التفرد مضمون
داخل `command/profile` فقط عبر لاحقة `_2`. تشغيل profileين في نفس الدقيقة
يعطي نفس `run_id`.

**الحل**: `run_key = f"{profile_key}/{run_id}"` كمفتاح أساسي. يحلّ
المشكلة كاملة، ويظل مقروءاً بشرياً بخلاف UUID.

### 8. 🟢 توافق ملف قاعدة البيانات

`get_db_manager()` يخزّن المدير بالمسار المُحلّل (`database.py:48`).
تمرير `state/order_runs.db` يُنتج مديراً منفصلاً تماماً بلا أي تعديل على
الكود القائم. لا خطر هنا — ذُكر للتوثيق.

---

## القرارات المعمارية وأسبابها

### ملف منفصل، لا جدول في القاعدة الحالية

| العامل | `manual_review_decisions.db` | `order_runs.db` |
|---|---|---|
| الحجم | 327 KB مستقر | مئات MB متنامية |
| الطبيعة | قرارات بشرية | بيانات آلية |
| قابلية الاستعادة | ❌ لا مصدر آخر | ✅ من CSV |
| `synchronous` المناسب | `FULL` | `NORMAL` |
| الحذف | لا يُحذف أبداً | دوري |
| تكرار الكتابة | نادر | مرة لكل عنصر |

خلط الاثنين يعني أن `VACUUM` على بيانات الـ runs يقفل قرارات المراجعة،
وأن نسخ قرارات المراجعة ينسخ مئات MB معها. الفصل صحيح.

**الربط بينهما** يبقى ممكناً بـ `item_key` لأن الجدولين يستخدمان
`hint_key()` نفسها. إن احتُجت `JOIN` حقيقياً: `ATTACH DATABASE`.

### مفاتيح طبيعية، لا `AUTOINCREMENT`

مع كتابة من عمليات متوازية، المفتاح الصناعي يفرض قراءة `lastrowid` بعد
كل إدخال وتنسيقاً بين العمليات. المفتاح الطبيعي (`store_product_id`,
`item_key`) يُحسَب محلياً في كل عامل بلا اتصال.

الثمن: مفاتيح نصية أكبر وفهارس أثقل قليلاً. مقايضة صحيحة عند هذا الحجم.

### `is_winner` عمود، لا جدول منفصل

البديل: جدول `run_winners` بصف لكل (run, item). لكن الفائز **دائماً**
موجود في `run_item_stores`، فجدول منفصل تكرار خالص يفتح باب تضارب بين
المصدرين.

### `rank_by_discount` محسوب مسبقاً

الترتيب داخل run منتهٍ لا يتغير أبداً. حسابه بـ window function في كل
استعلام هدر متكرر لنتيجة ثابتة. عمود واحد يحوّل «أفضل 3 مخازن» من
`ROW_NUMBER() OVER (...)` إلى `WHERE rank_by_discount <= 3`.

### Views في المخطط، لا في الكود

`v_run_winners`, `v_best_discount_per_item`, `v_run_summary` مُعرَّفة في
DDL. الفائدة: منطق الربط في مكان واحد، وتغيير المخطط لا يكسر كل استدعاء.

### لا ORM

المشروع لا يحتوي SQLAlchemy ولا SQLModel. طبقة
`DatabaseManager`/`DatabasePool`/`DatabaseQueries` كافية وواضحة، وإضافة
ORM لستة جداول ثابتة المخطط تكلفة بلا مقابل. كما أن ORM سيخفي `UPSERT`
و`BEGIN IMMEDIATE` — وهما تحديداً ما نحتاج التحكم فيه.

### CSV يبقى

الأسباب:
- `artifacts/` مصدر التشخيص، `matching_trace` لا مكان له في القاعدة
- Streamlit ينزّل الملفات للمستخدم
- شبكة أمان `db-import` تحتاج مصدراً
- `docs/order_summary_columns_audit_20260710/` يوثّق العقد الحالي

القاعدة **تُضيف** قدرة التحليل التاريخي، لا تستبدل المخرجات.

---

## أسئلة مفتوحة تحتاج تحققاً عملياً

1. **هل تحتوي حمولة `get_store_details` على `storeId`؟**
   الحمولة المفحوصة هي حمولة البحث لا المخازن. يُحدَّد في المرحلة 3 بطبع
   الحمولة الخام مرة واحدة. إن غاب `storeId`، الاسم هو الهوية الوحيدة.

2. **هل تحتوي صفوف المخازن على `salePrice`؟**
   إن حملت السعر بمفتاح مختلف، `first_discount_value()`
   (`tawreed_pricing.py:13`) يعالج الخصم لكن السعر يحتاج فحصاً.

3. **`stockLevel: 0` مع `availableQuantity: 1`** — قيمتان متعارضتان
   ظاهرياً في نفس الحمولة. `availableQuantity` هو المستخدم في المنطق
   (`tawreed_store_selection.py:64`). معنى `stockLevel` غير معروف؛ يُخزَّن
   للمرجعية أو يُترك.

4. **مسار DOM fallback** — `_dom_candidate()` (`tawreed_dom.py:49`)
   يُنتج `storeProductId: "dom-row-<...>"` وهو **ليس معرّفاً قابلاً
   للطلب**. `candidate_store_product_id()` ستُرجعه لأنها لا تفحص البادئة.
   يجب استثناء صفوف `dom-` من جدول `products` أو وسمها بعمود
   `is_synthetic` صراحةً — وإلا ستُملأ القاعدة بمنتجات وهمية.

هذه الأربعة **تُحل بالفحص، لا بالتصميم**. سجّل النتيجة في هذا الملف عند
تنفيذ المرحلة 3.
