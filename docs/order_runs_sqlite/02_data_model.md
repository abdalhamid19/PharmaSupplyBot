# 02 — نموذج البيانات المقترح

## مبدأ التصميم

المخطط يفصل بين ثلاثة أشياء مختلفة الطبيعة:

| الطبيعة | مثال | الجدول |
|---|---|---|
| ما لا يتغير عبر الزمن | كود الصنف، اسم المخزن، معرّف المنتج | `items`, `stores`, `products` |
| ما يتغير كل run | الكمية المتاحة، السعر، الخصم | `run_item_stores` |
| قرار حدث مرة واحدة | من فاز، لماذا، هل أُضيف للسلة | `run_items` |

هذا هو نمط **star schema**: جداول أبعاد صغيرة ثابتة + جدول حقائق كبير
ينمو. البديل (جدول واحد عريض يعيد كتابة اسم الصنف واسم المخزن في كل صف)
سيضاعف حجم القاعدة ويجعل تغيير اسم مخزن في Tawreed يظهر كأنه مخزن جديد.

## القرار: تطبيع بمفاتيح طبيعية، لا بمفاتيح صناعية

لن نستخدم `INTEGER PRIMARY KEY AUTOINCREMENT` للأبعاد. السبب: أثناء
الكتابة من عمليات متوازية (`item_workers > 1`) سيحتاج كل عامل إلى قراءة
المعرّف المتولد بعد الإدخال، وهذا يفرض تنسيقاً بين العمليات. المفتاح
الطبيعي (`store_product_id` من Tawreed، `item_key` المطبّع) يسمح لكل عامل
بحساب المفتاح محلياً دون قراءة.

## المخطط الكامل

الملف: `src/core/database/order_runs_schema.py`

### 1. `runs` — سجل لكل تشغيل

```sql
CREATE TABLE IF NOT EXISTS runs (
    run_key            TEXT PRIMARY KEY,   -- '<profile>/<run_id>' فريد عالمياً
    run_id             TEXT NOT NULL,      -- '20260830_1809'
    profile_key        TEXT NOT NULL,      -- 'wardany'
    command            TEXT NOT NULL DEFAULT 'order',
    started_at         TEXT NOT NULL,      -- ISO-8601 UTC
    finished_at        TEXT,               -- NULL أثناء التشغيل
    mode               TEXT NOT NULL DEFAULT '',   -- 'order' | 'match-only'
    execution_mode     TEXT NOT NULL DEFAULT '',   -- auto | api | browser
    warehouse_mode     TEXT NOT NULL DEFAULT '',
    min_discount_pct   REAL,
    matching_risk      TEXT NOT NULL DEFAULT '',
    excel_source       TEXT NOT NULL DEFAULT '',
    item_workers       INTEGER NOT NULL DEFAULT 1,
    artifact_dir       TEXT NOT NULL DEFAULT '',
    total_items        INTEGER NOT NULL DEFAULT 0,
    schema_version     INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_profile ON runs(profile_key, run_id);
```

**لماذا `run_key` وليس `run_id` فقط؟** لأن `run_id` هو طابع زمني بدقة
الدقيقة، وتشغيل profileين مختلفين في نفس الدقيقة يعطي نفس `run_id`.
`unique_run_id()` في `artifact_run.py:36` يضمن التفرد داخل
`command/profile` فقط.

**لماذا تُخزَّن إعدادات الـ run؟** لأن أي مقارنة بين runين بلا معرفة
`warehouse_mode` و`min_discount_pct` مقارنة بلا معنى: انخفاض الأسعار قد
يكون تغيّراً في السوق أو تغيّراً في `--warehouse-mode`.

### 2. `items` — بُعد الأصناف المطلوبة

```sql
CREATE TABLE IF NOT EXISTS items (
    item_key       TEXT PRIMARY KEY,   -- '<code_key>::<name_key>'
    item_code      TEXT NOT NULL DEFAULT '',
    item_name      TEXT NOT NULL DEFAULT '',
    first_seen_at  TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL
);
```

`item_key` يُبنى من `hint_key()` الموجود في
`src/core/manual_review/manual_review_hints.py:45` — نفس الدالة التي
تستخدمها قاعدة المراجعة اليدوية. **إعادة استخدامها إلزامية**، وإلا
سيستحيل الربط بين الجدولين لاحقاً.

`hint_key` يعالج: تنظيف `.0` من أكواد Excel، توحيد الأحرف الكبيرة، إزالة
كل ما ليس حرفاً عربياً/لاتينياً أو رقماً من الاسم.

### 3. `stores` — بُعد المخازن

```sql
CREATE TABLE IF NOT EXISTS stores (
    store_key      TEXT PRIMARY KEY,   -- 'storeId:1234' أو 'storeName:<اسم>'
    store_name     TEXT NOT NULL DEFAULT '',
    first_seen_at  TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL
);
```

مصدر `store_key`: `_store_identity()` في
`src/tawreed/store/tawreed_store_selection.py:55` — يجرّب
`storeProductId`, `productStoreId`, `storeId`, `supplierId`, `id` ثم يعود
إلى الاسم.

⚠️ **تحذير**: النسخة الحالية من `_store_identity` تُدرج `storeProductId`
أولاً، وهو معرّف **منتج-في-مخزن** لا معرّف مخزن. استخدامه كهوية مخزن
سيُنتج صفاً جديداً في `stores` لكل (منتج، مخزن). لهذا يجب أن يستخدم
الجدول دالة منفصلة `store_identity_key()` تبدأ من `storeId`/`supplierId`
وتتجاهل `storeProductId`. التفصيل في `07_risks_and_decisions.md`.

### 4. `products` — بُعد منتجات Tawreed

```sql
CREATE TABLE IF NOT EXISTS products (
    store_product_id  TEXT PRIMARY KEY,   -- المعرّف القابل للطلب
    product_id        TEXT NOT NULL DEFAULT '',
    name_ar           TEXT NOT NULL DEFAULT '',
    name_en           TEXT NOT NULL DEFAULT '',
    first_seen_at     TEXT NOT NULL,
    last_seen_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id);
CREATE INDEX IF NOT EXISTS idx_products_name_en    ON products(name_en);
```

`store_product_id` يُستخرج بـ `candidate_store_product_id()` من
`src/core/matching/candidate_identity.py:16` — يعالج التطبيع (`.0`,
`none`, `nan`) والحقول المتداخلة.

### 5. `run_items` — الحقيقة على مستوى العنصر (صف لكل run×item)

```sql
CREATE TABLE IF NOT EXISTS run_items (
    run_key                  TEXT NOT NULL REFERENCES runs(run_key)
                                  ON DELETE CASCADE,
    item_key                 TEXT NOT NULL REFERENCES items(item_key),
    requested_qty            INTEGER NOT NULL DEFAULT 0,
    ordered_qty              INTEGER NOT NULL DEFAULT 0,
    status                   TEXT NOT NULL DEFAULT '',
    reason                   TEXT NOT NULL DEFAULT '',
    matched                  INTEGER NOT NULL DEFAULT 0,
    manual_review_required   INTEGER NOT NULL DEFAULT 0,
    manual_review_category   TEXT NOT NULL DEFAULT '',
    matched_query            TEXT NOT NULL DEFAULT '',
    deterministic_score      REAL,
    winner_store_product_id  TEXT REFERENCES products(store_product_id),
    winner_store_key         TEXT REFERENCES stores(store_key),
    tie_break_reason         TEXT NOT NULL DEFAULT '',
    candidates_considered    INTEGER NOT NULL DEFAULT 0,
    stores_offering          INTEGER NOT NULL DEFAULT 0,
    elapsed_seconds          REAL NOT NULL DEFAULT 0,
    match_elapsed_seconds    REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (run_key, item_key)
);
CREATE INDEX IF NOT EXISTS idx_run_items_item   ON run_items(item_key, run_key);
CREATE INDEX IF NOT EXISTS idx_run_items_status ON run_items(status);
CREATE INDEX IF NOT EXISTS idx_run_items_review
    ON run_items(manual_review_required) WHERE manual_review_required = 1;
```

`PRIMARY KEY (run_key, item_key)` يجعل الكتابة **idempotent**: إعادة
استيراد نفس الـ run لا تُنتج تكراراً، والـ `UPSERT` يُحدّث الصف الموجود.
هذا ما يجعل «الكتابة المباشرة + أمر إعادة الاستيراد» آمناً معاً.

الفهرس الجزئي `WHERE manual_review_required = 1` أصغر بكثير من فهرس كامل
لأن معظم الصفوف صفر.

### 6. `run_item_stores` — الجدول الأهم: كل المخازن لكل صنف

```sql
CREATE TABLE IF NOT EXISTS run_item_stores (
    run_key            TEXT NOT NULL REFERENCES runs(run_key)
                            ON DELETE CASCADE,
    item_key           TEXT NOT NULL REFERENCES items(item_key),
    store_product_id   TEXT NOT NULL REFERENCES products(store_product_id),
    store_key          TEXT NOT NULL REFERENCES stores(store_key),
    available_qty      INTEGER NOT NULL DEFAULT 0,
    public_price       REAL,     -- retailPrice — سعر الجمهور
    purchase_price     REAL,     -- salePrice   — ما تدفعه أنت فعلاً
    discount_percent   REAL,
    currency           TEXT NOT NULL DEFAULT '',
    priority           INTEGER,
    is_winner          INTEGER NOT NULL DEFAULT 0,
    ordered_qty        INTEGER NOT NULL DEFAULT 0,
    rank_by_discount   INTEGER,
    source             TEXT NOT NULL DEFAULT '',  -- store_details|search|dom
    captured_at        TEXT NOT NULL,
    PRIMARY KEY (run_key, item_key, store_product_id)
);
CREATE INDEX IF NOT EXISTS idx_ris_store
    ON run_item_stores(store_key, run_key);
CREATE INDEX IF NOT EXISTS idx_ris_product
    ON run_item_stores(store_product_id, run_key);
CREATE INDEX IF NOT EXISTS idx_ris_winner
    ON run_item_stores(run_key, item_key) WHERE is_winner = 1;
CREATE INDEX IF NOT EXISTS idx_ris_discount
    ON run_item_stores(run_key, discount_percent DESC);
```

هذا هو الجدول الذي يجيب على سؤالك الأصلي حرفياً: «الأصناف والمخازن التي
توفرها والكمية المتوفرة في كل مخزن مع سعر الشراء والبيع وقيمة الخصم
وتحديد أعلى مخزن لكل صنف لكل run».

**`is_winner` وليس عمود `winner` في جدول منفصل**: صف واحد لكل (run, item)
يحمل `is_winner=1`. عند التقسيم على عدة مخازن، أكثر من صف يحمل
`ordered_qty > 0` — و`is_winner` يعني «المخزن الذي اختارته الاستراتيجية
أولاً». هذا يفصل «المُختار» عن «المُشترى منه».

**`rank_by_discount`**: مُحسوب مسبقاً عند الكتابة. الترتيب داخل الـ run
لا يتغير أبداً، فحسابه في كل استعلام هدر. يجعل سؤال «أفضل ثلاثة مخازن
لهذا الصنف» مجرد `WHERE rank_by_discount <= 3`.

**`purchase_price` و`public_price` بأسماء واضحة** — لا تنقل التسمية
المضلِّلة من CSV.

### 7. `run_candidates` — اختياري: المرشحون والمرفوضون

```sql
CREATE TABLE IF NOT EXISTS run_candidates (
    run_key           TEXT NOT NULL REFERENCES runs(run_key)
                           ON DELETE CASCADE,
    item_key          TEXT NOT NULL REFERENCES items(item_key),
    candidate_rank    INTEGER NOT NULL,
    store_product_id  TEXT NOT NULL DEFAULT '',
    name_ar           TEXT NOT NULL DEFAULT '',
    name_en           TEXT NOT NULL DEFAULT '',
    query             TEXT NOT NULL DEFAULT '',
    total_score       REAL,
    accepted          INTEGER NOT NULL DEFAULT 0,
    rejection_reason  TEXT NOT NULL DEFAULT '',
    candidate_source  TEXT NOT NULL DEFAULT '',
    is_best_match     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_key, item_key, candidate_rank)
);
```

**اجعله خلف مفتاح إعداد `store_candidates: false` افتراضياً.** الأساس:
`match_only_summary` يبلغ 133 KB لـ run صغير — أي ~10× حجم
`order_item_summary`. تخزين كل المرشحين لكل run سيجعل القاعدة تنمو أسرع
من كل الجداول الأخرى مجتمعة. أضِفه عند الحاجة لتحليل أسباب الرفض، لا
افتراضياً.

### 8. `schema_meta` — نسخة المخطط

```sql
CREATE TABLE IF NOT EXISTS schema_meta (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
```

`INSERT OR REPLACE INTO schema_meta VALUES ('schema_version', '1')`.
يُقرأ عند الإقلاع؛ إن كانت النسخة أقدم تُشغَّل ترقية. هذا أنظف من
`_ensure_column` المتكرر في `manual_review_store.py:132-135`.

## Views للاستعلامات المتكررة

```sql
-- الفائز لكل صنف في كل run مع كل التفاصيل مسطّحة
CREATE VIEW IF NOT EXISTS v_run_winners AS
SELECT r.run_key, r.run_id, r.profile_key, r.started_at,
       i.item_code, i.item_name,
       ri.requested_qty, ri.ordered_qty, ri.status,
       s.store_name, p.name_en, p.name_ar,
       ris.available_qty, ris.public_price, ris.purchase_price,
       ris.discount_percent, ris.currency
FROM run_items ri
JOIN runs   r  ON r.run_key = ri.run_key
JOIN items  i  ON i.item_key = ri.item_key
LEFT JOIN run_item_stores ris
       ON ris.run_key = ri.run_key
      AND ris.item_key = ri.item_key
      AND ris.is_winner = 1
LEFT JOIN stores   s ON s.store_key = ris.store_key
LEFT JOIN products p ON p.store_product_id = ris.store_product_id;

-- أفضل مخزن بالخصم لكل صنف لكل run
CREATE VIEW IF NOT EXISTS v_best_discount_per_item AS
SELECT run_key, item_key, store_key, store_product_id,
       discount_percent, purchase_price, available_qty
FROM run_item_stores
WHERE rank_by_discount = 1;

-- ملخص كل run
CREATE VIEW IF NOT EXISTS v_run_summary AS
SELECT r.run_key, r.run_id, r.profile_key, r.started_at, r.mode,
       COUNT(*)                                        AS items,
       SUM(ri.matched)                                 AS matched,
       SUM(ri.manual_review_required)                  AS flagged,
       SUM(CASE WHEN ri.status='no-results' THEN 1 END) AS no_results,
       SUM(ri.ordered_qty)                             AS total_ordered
FROM runs r JOIN run_items ri ON ri.run_key = r.run_key
GROUP BY r.run_key;
```

`v_run_summary` يُغني عن `compute_quality_metrics()`
(`src/core/quality/quality_metrics.py:98`) التي تقرأ CSV وتعدّ في Python.

## ما لا يُخزَّن، وسبب ذلك

| البيان | القرار | السبب |
|---|---|---|
| 11 عمود توقيت لكل عنصر | لا | تشخيص أداء لحظي، ليس تحليلاً تاريخياً. اثنان يكفيان |
| `api_raw_candidate_json` | لا | مضاعفة للأعمدة المُطبَّعة، يُضخّم القاعدة بلا فائدة |
| `matching_trace` (46 KB/run) | لا | تشخيص خالص، يبقى في `artifacts/` |
| `manual_review` rows | لا | لها قاعدتها بالفعل. أضف `JOIN` بالـ `item_key` |
| `searched_queries` | لا | نص طويل متكرر. `matched_query` يكفي |

المبدأ: `artifacts/` تبقى المصدر الكامل للتشخيص، وقاعدة البيانات تحمل
الحقائق القابلة للتحليل فقط. لا تحاول استبدال الملفات كلياً.

## تقدير الحجم

لـ run بـ 300 صنف ومتوسط 15 مخزناً للصنف:

| الجدول | صفوف/run | بايت/صف تقديري | المجموع |
|---|---|---|---|
| `run_items` | 300 | ~250 | 75 KB |
| `run_item_stores` | 4,500 | ~120 | 540 KB |
| `runs` | 1 | ~300 | — |
| الأبعاد | نمو ضئيل بعد أول runين | — | — |

≈ 0.6 MB لكل run كامل. 500 run ≈ 300 MB — مقبول تماماً لـ SQLite.
مع `run_candidates` مُفعَّلاً سيتضاعف ثلاث مرات، وهذا سبب إضافي لإبقائه
معطلاً افتراضياً.
