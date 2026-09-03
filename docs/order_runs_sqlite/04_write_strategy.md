# 04 — استراتيجية الكتابة

## المبدأ الحاكم: قاعدة البيانات لا يجوز أن تُفشل الـ run

هذا القرار الأهم في الميزة كلها. الـ `order run` يتفاعل مع موقع خارجي،
يستهلك وقتاً طويلاً، وقد يضيف عناصر فعلية إلى سلة الشراء. إذا انفجر
`sqlite3.OperationalError` في منتصف run بعد 200 صنف، فقد المستخدم عملاً
لا يمكن استعادته لأن العناصر أُضيفت للسلة بالفعل.

```python
def _persist_run_item_to_db(profile_key, item, summary, decision, row) -> None:
    """Persist one order-run item to SQLite; never fail the run."""
    if not _db_enabled():
        return
    try:
        store = get_order_runs_store()
        store.upsert_run_item(...)
    except Exception:
        logger.warning(
            "order-run DB write failed (non-fatal)",
            extra={"profile": profile_key, "item_code": item.code},
            exc_info=True,
        )
```

`except Exception` عريض هنا **مقصود ومبرَّر**، لا إهمالاً. الملف CSV يبقى
المصدر الكامل، وأمر `db-import` يمكنه إصلاح أي فجوة لاحقاً. هذا هو السبب
الحقيقي وراء وجود المسارين معاً: المسار المباشر سريع لكن قابل للفقد،
والمسار الاستيرادي بطيء لكن كامل.

المشروع يتبع هذا النمط أصلاً (`logger.debug("... (non-fatal)")` في
عشرات المواضع)، فهذا اتساق لا استثناء.

## التزامن

### الوضع أحادي العامل (`item_workers = 1`)

بسيط. اتصال واحد، معاملة لكل عنصر. لا مشكلة.

### الوضع متعدد العمليات (`item_workers > 1`)

`multiprocessing` بسياق `spawn`. كل عامل عملية منفصلة تكتب إلى نفس
الملف. الإعدادات المطلوبة عند كل اتصال:

```python
conn.execute("PRAGMA journal_mode=WAL")     # كاتب واحد + قرّاء متعددون
conn.execute("PRAGMA busy_timeout=30000")   # انتظر بدل الفشل الفوري
conn.execute("PRAGMA synchronous=NORMAL")   # كافٍ مع WAL، أسرع كثيراً
conn.execute("PRAGMA foreign_keys=ON")
```

`DatabasePool` الحالي يضبط `journal_mode=WAL` مرة واحدة في `connect()`
(`database_pool.py:30`) — وهذا صحيح لأن WAL خاصية دائمة للملف. لكنه يمرر
`timeout=30.0` إلى `sqlite3.connect` بدلاً من `busy_timeout` PRAGMA.
الاثنان متكافئان وظيفياً في CPython، فلا حاجة للتغيير.

`synchronous=NORMAL` غير مضبوط حالياً وهو الافتراضي `FULL`. مع WAL،
`NORMAL` آمن (لا يفقد إلا في انهيار نظام التشغيل، لا انهيار العملية) وأسرع
بمراتب. لبيانات تحليلية قابلة لإعادة الاستيراد هذه مقايضة صحيحة.

### لماذا لا يوجد قفل على مستوى التطبيق؟

لأن كل كتابة معاملة قصيرة جداً (بضعة INSERTs لعنصر واحد) وWAL يسمح
للقرّاء بالعمل أثناءها. مع `busy_timeout=30s` وكتابة تستغرق ميلي ثانية،
احتمال التصادم الفعلي ضئيل، والانتظار يحلّه. إضافة
`multiprocessing.Lock` هنا ستُبطئ كل شيء لحلّ مشكلة تحلّها SQLite بنفسها.

⚠️ **ملاحظة على الكود القائم**: `ManualReviewStore._schema_initialized_db_ids`
(`manual_review_store.py:58`) هو **متغير صنف** يُشارَك عبر كل النسخ في
العملية. هذا يعمل داخل عملية واحدة، لكن مع `spawn` تبدأ كل عملية بمجموعة
فارغة فيُعاد تشغيل الـ DDL. `CREATE TABLE IF NOT EXISTS` idempotent فلا
ضرر، لكن كل عامل يدفع تكلفة الـ DDL مرة. لا تنسخ هذا النمط — استخدم
`schema_meta` لفحص واحد بقراءة واحدة.

## المعاملات

الكتابة لكل عنصر تشمل عدة جداول. يجب أن تكون معاملة واحدة:

```python
def upsert_run_item(self, run_key, item_row, store_rows, ...) -> None:
    """Persist one item's facts and all its offering stores atomically."""
    with self.db.get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(UPSERT_ITEM, ...)          # items
            conn.executemany(UPSERT_STORE, ...)     # stores
            conn.executemany(UPSERT_PRODUCT, ...)   # products
            conn.execute(UPSERT_RUN_ITEM, ...)      # run_items
            conn.executemany(UPSERT_RUN_ITEM_STORE, ...)  # run_item_stores
            conn.commit()
        except Exception:
            conn.rollback()
            raise
```

`BEGIN IMMEDIATE` وليس `BEGIN` العادي: يحصل على قفل الكتابة فوراً بدلاً
من ترقيته لاحقاً، وهذا يمنع `SQLITE_BUSY` في منتصف المعاملة — وهي الحالة
التي لا يحلّها `busy_timeout`.

`executemany` للمخازن: 15 مخزناً في استدعاء واحد بدلاً من 15 دورة ذهاب
وعودة.

⚠️ **ملاحظة**: `DatabaseQueries.execute_update()` الحالي
(`database_queries.py:28`) يعمل `commit()` بعد كل استعلام. **لا تستخدمه**
للكتابة متعددة الجداول — استخدم `get_connection()` مباشرة وتحكّم في
المعاملة يدوياً.

## عدم التكرار (Idempotency)

كل جدول حقائق له `PRIMARY KEY` مركّب، وكل كتابة `UPSERT`:

```sql
INSERT INTO run_items (run_key, item_key, requested_qty, ...)
VALUES (?, ?, ?, ...)
ON CONFLICT(run_key, item_key) DO UPDATE SET
    requested_qty = excluded.requested_qty,
    status        = excluded.status,
    ...;
```

للأبعاد، نمط مختلف — لا تُدهس البيانات، حدِّث `last_seen_at` فقط:

```sql
INSERT INTO stores (store_key, store_name, first_seen_at, last_seen_at)
VALUES (?, ?, ?, ?)
ON CONFLICT(store_key) DO UPDATE SET
    store_name   = CASE WHEN excluded.store_name <> ''
                        THEN excluded.store_name ELSE store_name END,
    last_seen_at = excluded.last_seen_at;
```

الـ `CASE` مهم: إذا وصل صف بمخزن باسم فارغ (يحدث عندما تفشل
`store_name()` في `tawreed_store_summary.py:28` في إيجاد أي مفتاح
معروف)، لا يجوز أن يمحو اسماً صحيحاً سُجِّل سابقاً.

نتيجة هذا التصميم: **إعادة تشغيل `db-import` على نفس الـ run آمنة
تماماً**، وتشغيله على run كُتب مباشرة سيصلح الصفوف الناقصة فقط.

## أمر إعادة الاستيراد

```bash
# استيراد run محدد
python run.py db-import --run-dir artifacts/order/wardany/20260830_1809

# استيراد كل runs profile
python run.py db-import --profile wardany --all-runs

# فحص بلا كتابة
python run.py db-import --profile wardany --all-runs --dry-run
```

يُسجَّل عبر `@register("db-import")` في `src/cli/registry.py` ويُعرَّف في
`typer_app.py` كأي أمر آخر — لا يحتاج بنية جديدة.

### ما يمكنه استعادته وما لا يمكنه

| الجدول | من CSV؟ |
|---|---|
| `runs` | ✅ من اسم المجلد + عدد الصفوف |
| `items` | ✅ من `item_code`, `item_name` |
| `run_items` | ✅ كامل من `order_item_summary` |
| `products` | ✅ من حقول `matched_*` و`api_*` |
| `stores` (الفائز) | ✅ من `selected_store_name` |
| `run_item_stores` | ⚠️ **الفائز فقط** |
| `run_candidates` | ✅ من `match_only_summary` إن وُجد |

**هذا القيد جوهري، ولا يُصلح بأي مقدار من الكود.** بيانات كل المخازن
غير مكتوبة في أي ملف، فلا مصدر لاستعادتها. الـ runs السابقة (بما فيها
الـ run الفعلي `20260830_1809` في المستودع) لن تحصل على صفوف المخازن
غير الفائزة أبداً.

النتيجة العملية: عمود `source` في `run_item_stores` يجب أن يميّز
`'store_details'` (بيانات كاملة) عن `'csv_import'` (الفائز فقط)، وإلا
سيبدو run مستورد كأن كل صنف فيه له مخزن واحد — وهذا سيُفسد أي إحصاء
لعدد المخازن عبر الزمن.

### التوصية

نفّذ نقاط الالتقاط (`03_capture_points.md`) **قبل** الاعتماد على أي تحليل
للمخازن. الـ runs القديمة تُستورد للحصول على `run_items` التاريخي
(الحالات، الأسعار الفائزة، معدلات المطابقة) وهذا مفيد بذاته، لكن تحليل
المخازن يبدأ من أول run جديد فقط.

## الإعداد في `config.yaml`

```yaml
database:
  order_runs_enabled: true
  order_runs_path: state/order_runs.db
  store_candidates: false        # صفوف المرشحين — يُضخّم الحجم 3×
  store_all_offering_stores: true
```

مع `DatabaseConfig` في `config_models.py` و`build_database_config` في
`config_factory.py` — نفس نمط `MatchingConfig` و`RuntimeConfig` القائم.

القيمة الافتراضية `order_runs_enabled: true` لكن كل مسارات الكتابة
محمية بـ `try/except`، فالتفعيل الافتراضي لا يحمل خطراً. من يريد التعطيل
يضبطه `false` أو يحدد `SQLITE_ORDER_RUNS_PATH=""` في البيئة.

## النسخ الاحتياطي والصيانة

`state/` مُستثنى من git، فالقاعدة لن تُرفَع. للنسخ الاحتياطي:

```bash
# نسخة آمنة أثناء التشغيل — لا تنسخ الملف بـ copy مع WAL
sqlite3 state/order_runs.db ".backup state/order_runs_backup.db"
```

⚠️ لا تنسخ `order_runs.db` بـ `Copy-Item` أثناء وجود كتّاب: مع WAL توجد
بيانات في `-wal` غير مدمَجة، والنسخة ستكون ناقصة. استخدم `.backup` أو
`VACUUM INTO`.

للصيانة الدورية:
```sql
PRAGMA wal_checkpoint(TRUNCATE);   -- دمج ملف WAL
VACUUM;                            -- استرجاع المساحة بعد حذف runs
ANALYZE;                           -- تحديث إحصاءات المُخطِّط
```

للحذف: `DELETE FROM runs WHERE started_at < '2026-01-01'` — و`ON DELETE
CASCADE` يتولى الباقي، بشرط أن يكون `PRAGMA foreign_keys=ON` مضبوطاً في
نفس الاتصال (وهو مضبوط في `database_pool.py:50`).
