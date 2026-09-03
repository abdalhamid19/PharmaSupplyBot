# تقرير إنجاز: التقاط snapshot للمخازن في قاعدة بيانات order runs

> **التاريخ:** 31 أغسطس 2026
> **الفرع:** `logging_system`
> **Commits:** `3b71b42` (الميزة الأساسية) + `fccc446` (إصلاح اكتشفه الاختبار الحي)

---

## 1. المشكلة التي حُلّت

### 1.1 قبل الميزة

نظام الصيدلية (PharmaSupplyBot) يطلب الأدوية من موقع Tawreed. عند معالجة كل صنف، تُظهر استراتيجية توزيع المخازن (warehouse strategy) **مخزناً واحداً فقط** هو الذي اختارته — ثم تتجاهل كل المخازن الأخرى التي تبيع نفس المنتج. النتيجة:

- **فقدان البيانات:** كل عروض المخازن البديلة تذهب هدراً بعد اكتمال الطلب.
- **لا إمكانية للتدقيق:** لا يمكن معرفة لاحقاً هل اختار النظام أفضل مخزن فعلاً، ولا كم كان خصم المخازن الأخرى.
- **لا ذاكرة تاريخية:** قاعدة بيانات `order_runs.db` كانت تسجل معلومات مستوى الصنف فقط (حالة، مطابقة، فائز) — لا معلومات مستوى المخزن.

### 1.2 بعد الميزة

لكل صنف في كل تشغيل، تُحفظ الآن **قائمة كاملة بكل المخازن** التي تبيع المنتج، مع بيانات السعر والخصم والكمية المتاحة، وتحديد صريح للمخزن الذي اختارته الاستراتيجية.

**القيمة العملية المباشرة:** يمكن الآن الإجابة على سؤال "كم مرة لم يختر النظام أفضل خصم؟" — وهذه كانت بيانات مستحيلة الاستخراج قبل الميزة (انظر مثال 4.2).

---

## 2. البنية المعمارية

### 2.1 طبقة الالتقاط (Tawreed layer)

ملفات جديدة في `src/tawreed/store/`:

| الملف | الدور |
|---|---|
| `tawreed_store_snapshot.py` | القلب التقني. يخزن صفوف المخازن والاختيارات على كائن البوت (`bot.last_store_rows`). يُصفَّر تلقائياً بين الأصناف لمنع **تسرب** مخازن صنف إلى الصنف التالي — خطأ خطير لأنه يُنتج بيانات تبدو صحيحة وهي خاطئة. |
| `tawreed_store_run_payload.py` | يبني الحمولة التي تنتقل من البوت إلى كاتب الـ artifacts. |
| `tawreed_store_match_only.py` | منطق مشترك لمسار match-only: يسجل المخزن المختار بكمية **صفر** (لأن match-only لا يضيف للسلة قط). |

### 2.2 نقاط الالتقاط في مسارات التشغيل

الميزة تغطي **أربعة مسارات** مستقلة:

| المسار | الملف المعدل | آلية الالتقاط |
|---|---|---|
| المتصفح — مخزن واحد | `tawreed_products_flow.py` | بعد إضافة ناجحة: صف البحث نفسه هو المخزن (source=`search`) + الكمية المطلوبة |
| المتصفح — متعدد المخازن | `tawreed_products_flow.py` | اعتراض استجابة الشبكة `store-details` (source=`store_details`) + اختيار الاستراتيجية |
| API — مخزن واحد | `tawreed_api_flow_cart.py` | صف البحث + الكمية (source=`search`) |
| API — متعدد المخازن | `tawreed_api_flow_multistore.py` | استدعاء `get_store_details` + اختيارات التوزيع الكمي |

ومسار match-only في كلا الوضعين (`tawreed_match_only_metadata.py` و`tawreed_api_match_only_metadata.py`) يسجل **ماذا كانت ستختار الاستراتيجية** دون لمس السلة.

### 2.3 طبقة قاعدة البيانات (`src/core/database/`)

| الملف الجديد | الدور |
|---|---|
| `order_runs_stores.py` | بناء صفوف الحقائق لجدول `run_item_stores` — صف واحد لكل (run × صنف × مخزن) |
| `order_runs_store_values.py` | استخراج السعر العام (`retailPrice`) وسعر الشراء (`salePrice`) والخصم والعملة، مع كشف الصفوف الاصطناعية (`dom-row-`) |
| `order_runs_store_ranking.py` | تصفية الصفوف القابلة للحفظ (لا بد من `storeProductId` حقيقي وهوية مخزن صالحة)، إزالة التكرار، وحساب **ترتيب الخصم مسبقاً** حتى لا تحتاج الاستعلامات window functions |
| `order_runs_snapshot_writer.py` | كتابة الـ snapshot **ذرياً** مع صف الصنف: إعادة كتابة كاملة (حذف ثم إدراج) لكل run_key، فلا تبقى بقايا من تشغيل سابق |
| `order_runs_dimensions.py` | جدولا الأبعاد `products` و`stores` (UPSERT — تتكرر عبر الـ runs ولا تتضخم) |
| `order_runs_write_plan.py` | خطة الكتابة الموحدة |

### 2.4 المخطط النهائي لجدول `run_item_stores`

```sql
CREATE TABLE run_item_stores (
    run_key            TEXT,      -- التشغيل
    item_key           TEXT,      -- الصنف
    source             TEXT,      -- 'store_details' أو 'search'
    store_product_id   TEXT,      -- معرف Tawreed القابل للطلب
    store_key          TEXT,      -- هوية المخزن المستقرة (storeName:... أو storeId:...)
    captured_at        TEXT,
    is_winner          INTEGER,   -- هل اختارته الاستراتيجية؟
    ordered_qty        INTEGER,   -- الكمية المطلوبة منه (0 في match-only)
    available_quantity INTEGER,   -- المخزون المتاح
    rank_by_discount   INTEGER,   -- 1 = أعلى خصم (محسوب مسبقاً)
    public_price       REAL,      -- سعر الجمهور (retailPrice)
    purchase_price     REAL,      -- سعر شراء الصيدلية (salePrice)
    discount_percent   REAL,      -- الخصم الفعلي
    currency           TEXT
)
```

> **ملاحظة تصميمية:** أسماء الحقول في القاعدة **مقابلة** لقيمتها الحقيقية، بينما CSV التاريخي يسميهما بالمقلوب (`winner_sale_price` يحمل سعر الجمهور). القاعدة تتبنى التسمية الصحيحة عمداً، مع توثيق عدم التطابق.

---

## 3. إصلاحا الخلل اللذان كشفهما الاختبار الحي

### 3.1 إصلاح 1: `winners=0` في وضع match-only (`3b71b42`)

**العَرَض:** أول تشغيل دخاني حقيقي (8 أصناف) سجّل 136 عرض مخزن لكن `winners=0` — لا فائزين إطلاقاً.

**السبب الجذري:** دالة `record_store_choice` كانت تُستدعى فقط في مسارات الطلب الفعلي. مسار match-only كان يسجل صفوف المخازن فقط، بدون تسجيل المخزن الذي اختارته الاستراتيجية.

**الإصلاح:** إنشاء `tawreed_store_match_only.py` الذي يستدعي `record_store_choice` بعد اختيار الاستراتيجية، مع `ordered_qty=0` — وهذا ما يميز بيانات match-only بوضوح في التحليلات: `is_winner=1` تعني "كان سيُختار"، و`ordered_qty=0` تعني "لم يُطلب فعلاً".

### 3.2 إصلاح 2: الصفوف بلا `productId` (`fccc446`)

**العَرَض:** في التشغيل الحي على 23 صنفاً، ظهرت 3 أصناف `matched-only` بلا مخازن وبلا فائز، رغم أن CSV أظهر مخزناً مختاراً لها.

**التشخيص (خطوة بخطوة):**

1. القاسم المشترك بين الثلاثة: مطابقة عبر **saved manual review**.
2. بحث API مباشر على أحدها كشف شكل الصف الفعلي:

```text
storeProductId: 2366987   ← موجود (قابل للطلب)
productsCount:  1         ← يوحي بمخزن واحد
productId:      None      ← لا يمكن استدعاء get_store_details به!
```

3. **السبب:** مسار match-only كان يفحص `productsCount > 0` فقط ليقرر أن الصنف "متعدد المخازن"، ثم يستدعي `get_store_details(None)` التي تحوّل `None` إلى قائمة فارغة، فيُرفع استثناء يُبتلع بصمت (`except Exception: logger.debug(...); return`) — فلا يُسجَّل أي شيء.
4. **الدليل التصميمي:** مسار الطلب الفعلي يعالج هذه الحالة صح (`tawreed_api_flow_cart.py:40-41`):

```python
has_product_id = bool(match.data.get("productId") or match.data.get("id"))
is_multi = int(match.data.get("productsCount") or 0) > 0 and has_product_id
```

**الإصلاح:** استخراج نفس القاعدة إلى `_can_fetch_store_details()` في مسار match-only: صف بلا `productId` (أو `productsCount ≤ 0`) يعني أن **صف البحث نفسه هو المخزن الوحيد**، فيُسجَّل مباشرة كمخزن وفائز (source=`search`) بدلاً من نداء API محكوم بالفشل.

**النتيجة بعد الإصلاح:** 3/3 أصناف سُجلت بمخزن وفائز وبيانات أسعار كاملة (انظر 4.3).

---

## 4. التحقق الحي — الأرقام الفعلية

### 4.1 تشغيل الدخان الأول (اكتشاف إصلاح 1)

```text
الأمر:  run.py order --profile wardany --excel _tmp_smoke_matched.xlsx --limit 8 --match-only --fast-search
النتيجة:  processed=8  matched=8  run_item_stores=136  winners=8  ordered_qty=0 ✓
```

### 4.2 التشغيل الحي الأول على SMALL_TEST.xlsx (اكتشاف إصلاح 2)

```text
run: wardany/20260831_1310
processed=23  matched=17  offering_rows=217  winners=14
→ 3 أصناف matched-only بلا مخازن ← الخلل الموصوف في 3.2
```

### 4.3 التشغيل الحي النهائي بعد الإصلاحين

```text
run: wardany/20260831_1331  (mode=match-only)
processed:            23
matched:              23
matched-only:         17  → كلها لديها مخازن وفائز (17/17) ✓
not-orderable:         6  → لا مخازن لها — صحيح: صفوفها بلا storeProductId أصلاً ✓
offering_store_rows: 221   → 218 من store_details + 3 من search ✓
winner_rows:          17
ordered_qty:           0  في كل الصفوف — صحيح تماماً لوضع match-only ✓
```

**دليل القيمة التحليلية** — بيانات لم تكن موجودة قبل الميزة (أصناف لم يختر النظام فيها أفضل خصم):

```text
74096  CAL MAG 30TAB       → فائز بخصم 21.0%  بينما الأفضل 33.5%
73528  CALCITRON 30 CAP    → فائز بخصم 25.0%  بينما الأفضل 36.5%
```

**الأصناف الثلاثة المُصلَحة** — سجلت الآن بمخزن وفائز وأسعار كاملة:

```text
83362  LIMITLESS PRENATAL MAX  → فارما سكاي   خصم 20%  (فائز، ordered_qty=0)
90846  CEFTRIAXONE 1GM SEDICO  → فارما توداي  خصم 22%  (فائز، ordered_qty=0)
85097  HEPTA PANTHENOL CREAM   → الفاروق       خصم 0%  (فائز، ordered_qty=0)
```

### 4.4 مثال على صف كامل من القاعدة

```text
30089  BEBELAC LF MILK  (7 عروض مخازن)
rank 1:  شركه اركان (الجيزه)      خصم 9.0%   متاح 7   ← الفائز
rank 2:  شركه البركه (الجيزه)     خصم 9.0%   متاح 2
rank 3:  شركه مصر مديكال (الجيزه) خصم 9.0%   متاح 5
rank 4:  شركه التحرير (الجيزه)    خصم 8.0%   متاح 12
...
```

---

## 5. الاختبارات

### 5.1 ملفات الاختبار الجديدة (4 ملفات، ~490 سطراً)

| الملف | ما يغطيه |
|---|---|
| `tests/core/database/test_order_runs_store_writer.py` | الكتابة الذرية، إعادة الكتابة بلا بقايا، سلامة المفاتيح الأجنبية |
| `tests/core/database/test_order_runs_stores.py` | بناء الصفوف، تصفية الصفوف غير القابلة للحفظ، إزالة التكرار، ترتيب الخصم |
| `tests/tawreed/store/test_tawreed_store_snapshot.py` | الالتقاط على البوت، **عدم التسرب بين الأصناف**، تجاهل القوائم الفارغة |
| `tests/tawreed/store/test_tawreed_store_choice.py` | تسجيل اختيار match-only بكمية صفر |
| `tests/tawreed/api/test_api_match_only_no_product_id.py` | إصلاح 2: صف بلا `productId` يسجل نفسه مخزناً + وفايزاً؛ وصف بـ `productId` ما زال يستدعي `get_store_details` |

### 5.2 بوابات الجودة

| البوابة | النتيجة |
|---|---|
| pytest (شاملة) | 614 اختباراً — errors=5 **موجودة مسبقاً** وغير مرتبطة (قائمة محددة أدناه) |
| الاختبارات المركزة | 147 passed, 6 skipped ✓ |
| `compileall` | نظيف ✓ |
| `rule_audit` (حدود حجم الملفات والدوال) | **0 مخالفات جديدة** (بعد استخراج helpers لتقصير الدوال) |
| تشغيل حي match-only ×2 | ناجح ومطابق ✓ |

الأخطاء الخمسة الموجودة مسبقاً (غير مرتبطة بهذا العمل): `test_load_order_items_rejects_prevented_file_as_order_excel`، `test_strict_api_match_only_failure_exits_without_traceback`، `test_strict_api_order_failure_exits_without_traceback`، `test_async_matching_logging_uses_queue_handler_and_stops_listener`، `test_remove_matching_cart_rows_counts_row_removed_despite_click_error`.

---

## 6. سجل التغييرات على GitHub

| Commit | الوصف | الملفات |
|---|---|---|
| `3b71b42` | feat: capture order run store snapshots | 27 ملفاً (+1399/−40): 10 ملفات src جديدة، 14 ملفاً معدلاً، 4 ملفات اختبار |
| `fccc446` | fix(api): record single-store search rows missing productId in match-only | ملفان (+79/−1) |

**لم يُرفع عمداً:** `state/wardany.json` (يحتوي رموز جلسة حساسة)، قواعد SQLite، ملفات Excel المؤقتة.

---

## 7. كيف تستهلك البيانات الجديدة؟

```sql
-- الأصناف التي لم يختر فيها النظام أفضل خصم (فرصة توفير)
SELECT r.item_key,
       w.discount_percent  AS winner_discount,
       MAX(b.discount_percent) AS best_available,
       MAX(b.discount_percent) - w.discount_percent AS missed_discount
FROM run_items r
JOIN run_item_stores w ON w.run_key = r.run_key
                      AND w.item_key = r.item_key
                      AND w.is_winner = 1
JOIN run_item_stores b ON b.run_key = r.run_key
                       AND b.item_key = r.item_key
WHERE r.run_key = 'wardany/20260831_1331'
GROUP BY r.item_key
HAVING best_available > winner_discount + 0.01
ORDER BY missed_discount DESC;

-- تاريخ أسعار مخزن معين عبر كل التشغيلات
SELECT run_key, item_key, purchase_price, discount_percent, available_quantity
FROM run_item_stores
WHERE store_key = 'storeName:شركه ابو عميره (الجيزه)'
ORDER BY captured_at DESC;

-- نسبة تغطية snapshot لكل تشغيل
SELECT run_key,
       SUM(matched)                          AS matched_items,
       SUM(stores_offering > 0)              AS items_with_stores,
       SUM(winner_store_key IS NOT NULL)     AS items_with_winner
FROM run_items
GROUP BY run_key;
```

---

## 8. المتبقي / التوصيات

1. **وضع الطلب الفعلي حيّاً:** المسار مغطى بالاختبارات والكود، لكن لم يُشغَّل طلب حقيقي ضد الموقع (تجنباً للمساس بالسلة دون توجيه). التشغيل بـ `--limit 1` في وضع الطلب يتحقق منه نهائياً.
2. **الأخطاء الخمسة القديمة** في الاختبارات الشاملة تستحق جلسة إصلاح مستقلة.
3. **استعلامات جاهزة:** يمكن لاحقاً إضافة view SQL للسؤال الأهم ("winner discount < best discount") داخل `order_runs_views.py`.
