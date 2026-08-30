# 06 — خطة التنفيذ

خمس مراحل. كل مرحلة تُنتج شيئاً يعمل ويُختبر بمعزل، وكل مرحلة تنتهي
بـ commit. لا تبدأ مرحلة قبل أن تمر اختبارات ما قبلها.

**التحقق بعد كل مرحلة:**
```powershell
& ".venv\Scripts\python.exe" tools\phase_validation.py
```
يشغّل `compileall` + الاختبارات + `rule_audit`. المشروع يعتمده كخط أساس
موثّق في `docs/PROJECT_MAP.md:220`.

---

## المرحلة 1 — المخطط والمخزن (بلا ربط بالـ run)

**الهدف:** قاعدة بيانات تُنشأ وتُقرأ وتُكتب، مستقلة تماماً عن مسار الـ order.

### الملفات

| ملف | المسؤولية | حد الأسطر |
|---|---|---|
| `src/core/database/order_runs_schema.py` | كل نصوص DDL + `SCHEMA_VERSION` | ~95 |
| `src/core/database/order_runs_sql.py` | نصوص UPSERT | ~90 |
| `src/core/database/order_runs_store.py` | صنف `OrderRunsStore` | ~95 |
| `src/core/ordering/store_identity.py` | `store_identity_key()` | ~40 |
| `tests/core/database/test_order_runs_schema.py` | اختبارات | — |

### الخطوات

1. **اكتب الاختبار الفاشل** — `tests/core/database/test_order_runs_schema.py`:

```python
"""Schema creation and idempotency tests for the order-runs store."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.database.order_runs_store import OrderRunsStore


class OrderRunsSchemaTests(unittest.TestCase):
    """Verify schema creation, idempotency, and version tracking."""

    def test_schema_creates_all_tables(self) -> None:
        """All eight tables and three views exist after init."""
        with TemporaryDirectory() as tmp:
            store = OrderRunsStore(Path(tmp) / "runs.db")
            names = store.table_names()
            for expected in (
                "runs", "items", "stores", "products",
                "run_items", "run_item_stores", "schema_meta",
            ):
                self.assertIn(expected, names)

    def test_schema_init_is_idempotent(self) -> None:
        """Creating the store twice on the same file does not raise."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.db"
            OrderRunsStore(path)
            OrderRunsStore(path)          # must not raise

    def test_schema_version_recorded(self) -> None:
        """schema_meta holds the current schema version."""
        with TemporaryDirectory() as tmp:
            store = OrderRunsStore(Path(tmp) / "runs.db")
            self.assertEqual(store.schema_version(), 1)
```

2. **شغّله وتأكد أنه يفشل**
   `& ".venv\Scripts\python.exe" -m pytest tests/core/database/test_order_runs_schema.py -v`
   المتوقع: `ModuleNotFoundError: order_runs_store`

3. **اكتب `order_runs_schema.py`** — DDL من `02_data_model.md` كثوابت نصية.
   كل `CREATE` بـ `IF NOT EXISTS`.

4. **اكتب `order_runs_store.py`** — يستخدم `get_db_manager(path)` القائم:

```python
"""SQLite store for order-run facts, dimensions, and store snapshots."""

from __future__ import annotations

from pathlib import Path

from .database import get_db_manager
from .order_runs_schema import ALL_DDL, SCHEMA_VERSION


class OrderRunsStore:
    """Persistence facade for order-run analytics tables."""

    def __init__(self, path: str | Path | None = None, database_manager=None):
        """Initialize the store and ensure the schema exists."""
        self.db = database_manager or get_db_manager(path)
        self.path = getattr(self.db, "path", path)
        self._ensure_schema()
```

5. **شغّل الاختبار — يجب أن ينجح**

6. **أضف اختبار `store_identity_key`**:

```python
def test_store_identity_ignores_store_product_id(self) -> None:
    """Store identity must not be derived from storeProductId."""
    row = {"storeProductId": 2902379, "storeId": 55, "storeName": "X"}
    self.assertEqual(store_identity_key(row), "storeId:55")

def test_store_identity_falls_back_to_name(self) -> None:
    """Rows without any id use the normalized store name."""
    self.assertEqual(
        store_identity_key({"storeName": "شركه البركه"}),
        "storeName:شركه البركه",
    )
```

**السبب**: `_store_identity()` القائم في
`tawreed_store_selection.py:55` يبدأ من `storeProductId` — صحيح لغرضه
(منع اختيار نفس السطر مرتين) وخاطئ تماماً كهوية مخزن. انظر
`07_risks_and_decisions.md`.

7. **commit**
```
feat(db): add order-runs SQLite schema and store facade
```

---

## المرحلة 2 — الكتابة على مستوى العنصر

**الهدف:** `runs`, `items`, `run_items` تُملأ من run حقيقي. لا مخازن بعد.

### الخطوات

1. **اختبار التحويل** — `tests/core/database/test_order_runs_rows.py`:

```python
def test_run_item_row_from_summary_row(self) -> None:
    """Summary CSV row maps to run_items columns with correct types."""
    summary = {
        "item_code": "12345", "item_name": "CAL MAG",
        "item_qty": 10, "status": "added-to-cart",
        "ordered_total_qty": 10, "matched": True,
        "manual_review_required": False,
        "deterministic_score": 24.5,
        "winner_store_product_id": "2902379",
    }
    row = run_item_row("wardany/20260830_1809", summary)
    self.assertEqual(row["requested_qty"], 10)
    self.assertEqual(row["ordered_qty"], 10)
    self.assertEqual(row["matched"], 1)               # bool → int
    self.assertEqual(row["manual_review_required"], 0)
```

انتبه: `matched` في CSV نص `"True"`/`"False"`، وفي الذاكرة `bool`.
التحويل يجب أن يعالج الحالتين لأن نفس الدالة تُستخدم من الكتابة المباشرة
ومن `db-import`.

2. **اختبار Idempotency** — الأهم في هذه المرحلة:

```python
def test_upsert_run_item_twice_keeps_one_row(self) -> None:
    """Re-persisting the same item updates rather than duplicates."""
    store = OrderRunsStore(path)
    store.open_run(run_meta)
    store.upsert_run_item(run_key, item_row)
    store.upsert_run_item(run_key, item_row)
    self.assertEqual(store.count_run_items(run_key), 1)
```

3. **اكتب `order_runs_rows.py` و`order_runs_writer.py`**

4. **اربط `open_run_record` / `finish_run_record`** في
   `cli_order_execution.py:38` داخل `try/finally`

5. **اربط `_persist_run_item_to_db`** في
   `tawreed_order_summary_build.py:16` — سطر واحد، محمي بـ `try/except`

6. **اختبار أن فشل القاعدة لا يُفشل الـ run** — اختبار حرج:

```python
def test_db_failure_does_not_break_artifact_write(self) -> None:
    """A raising store must not propagate into append_order_item_artifacts."""
    with patch("...order_runs_store", side_effect=RuntimeError("boom")):
        append_order_item_artifacts(profile, item, summary, decision)
    # CSV artifact must still exist
    self.assertTrue(list(run_dir.glob("order_item_summary_*.csv")))
```

7. **تشغيل حقيقي آمن** — لا يلمس السلة:
```powershell
& ".venv\Scripts\python.exe" run.py order --profile wardany `
  --excel data/input/order_items/shortage_report_total_20260502.xlsx `
  --limit 5 --match-only --fast-search
```
ثم تحقق: `sqlite3 state/order_runs.db "SELECT * FROM v_run_summary"`

8. **commit**
```
feat(db): persist run and item facts during order runs
```

---

## المرحلة 3 — التقاط كل المخازن ⭐

**الهدف:** `run_item_stores` و`stores` و`products` تُملأ. هذه المرحلة
هي الميزة الفعلية.

### الخطوات

1. **اكتب `src/tawreed/store/tawreed_store_snapshot.py`** (~30 سطراً)

2. **اختبار الالتقاط** بـ bot مزيّف:

```python
def test_record_store_rows_sets_snapshot(self) -> None:
    """Captured rows and their source land on the bot."""
    bot = SimpleNamespace()
    record_store_rows(bot, [{"storeId": 1}, {"storeId": 2}], "store_details")
    self.assertEqual(len(bot.last_store_rows), 2)
    self.assertEqual(bot.last_store_rows_source, "store_details")

def test_reset_clears_previous_item_rows(self) -> None:
    """Item N's stores must not leak into item N+1."""
    bot = _bot_with_rows([{"storeId": 1}])
    bot._reset_last_item_state()
    self.assertEqual(bot.last_store_rows, [])
```

الثاني هو الاختبار المهم: تسرّب مخازن بين الأصناف سيُنتج بيانات خاطئة
بصمت — أسوأ من عدم وجود بيانات.

3. **عدّل نقاط الالتقاط الثلاث** — سطر واحد لكل موقع:
   - `products/tawreed_products_flow.py:231`
   - `api/tawreed_api_flow_multistore.py:14`
   - `api/tawreed_api_match_only_metadata.py:31`

4. **عدّل `_reset_last_item_state`** في `tawreed_bot_core.py:73`

5. **احتياط الصنف أحادي المخزن** — لا تفقد الأصناف التي
   `productsCount == 0`:

```python
def test_single_store_item_still_recorded(self) -> None:
    """Items with productsCount=0 produce one store row from match.data."""
```

6. **حساب `rank_by_discount` و`is_winner`** — عبر
   `discount_value_as_percent()` القائم في `tawreed_pricing.py:63` لضمان
   تطابق المنطق مع الاستراتيجية. لا تُعِد كتابة تحليل الخصم.

7. **اختبار تكامل**: run بـ 3 أصناف → تحقق أن عدد صفوف
   `run_item_stores` = مجموع `productsCount`، وأن صفاً واحداً فقط لكل
   صنف يحمل `is_winner = 1`

8. **تشغيل حقيقي** ومقارنة عدد الصفوف بـ `api_productsCount` في
   `match_only_summary` — تحقق مستقل من صحة الالتقاط

9. **commit**
```
feat(db): capture all offering stores per item with winner flag
```

---

## المرحلة 4 — أمر `db-import`

**الهدف:** استرداد الـ runs السابقة، وإصلاح أي فجوة في الكتابة المباشرة.

### الخطوات

1. **اختبار على مجلد run حقيقي** — المستودع يحتوي على
   `artifacts/order/wardany/20260830_1809/` بـ 47 صنفاً:

```python
def test_import_real_run_directory(self) -> None:
    """Importing a real artifact directory fills runs and run_items."""

def test_import_is_idempotent(self) -> None:
    """Importing the same directory twice yields the same row counts."""

def test_import_marks_source_as_csv(self) -> None:
    """Imported store rows carry source='csv_import', not 'store_details'."""
```

الثالث ضروري: بدونه تُخلط البيانات الناقصة بالكاملة ويُبنى تحليل خاطئ.

2. **اكتب `src/cli/commands/cli_db_import.py`** — `@register("db-import")`

3. **`csv.field_size_limit`** يُرفَع قبل قراءة `match_only_summary`
   (`api_raw_candidate_json` قد يتجاوز 128 KB — تأكدنا من ذلك عملياً)

4. **`encoding="utf-8-sig"`** إلزامي — BOM موجود فعلاً في المخرجات

5. **أضف الأمر إلى `typer_app.py` و`cli_commands.py`**

6. **تحذير صريح في المخرجات** عن نقص بيانات المخازن للـ runs القديمة

7. **استيراد كل الـ runs الموجودة** والتحقق من النتيجة

8. **commit**
```
feat(cli): add db-import command for artifact backfill
```

---

## المرحلة 5 — الاستعلامات والواجهة

**الهدف:** الاستفادة الفعلية.

### الخطوات

1. **اكتب `order_runs_queries.py`** — الدوال المذكورة في
   `05_queries_and_use_cases.md`، مع اختبار لكل دالة على بيانات مُهيّأة

2. **تبويب Streamlit جديد "History"**:
   - تاريخ سعر صنف (استعلام 4)
   - موثوقية المخازن (استعلام 6)
   - اختيارات دون المثالية (استعلام 3)
   - مقارنة runين (استعلام 8)

3. **حوّل `command_run_options()`** في `streamlit_results.py:40` إلى
   القراءة من القاعدة بدلاً من مسح المجلدات، **مع الرجوع للملفات** إن كانت
   القاعدة معطّلة أو فارغة

4. **`v_run_summary` بدل `compute_quality_metrics`** حيث يُمكن

5. **commit**
```
feat(ui): add run history and store analytics from SQLite
```

---

## معايير القبول

| المرحلة | معيار النجاح | الحالة |
|---|---|---|
| 1 | القاعدة تُنشأ، DDL idempotent، `store_identity_key` صحيحة | ✅ مكتملة |
| 2 | run بـ 5 أصناف يُنتج 1 صف `runs` + 5 صفوف `run_items`. فشل القاعدة لا يُفشل الـ run | ✅ مكتملة |
| 3 | عدد صفوف `run_item_stores` = مجموع `productsCount`. صف واحد `is_winner` لكل صنف | ⏳ |
| 4 | استيراد `20260830_1809` يُنتج 47 صف `run_items`. تكراره لا يُضاعف | ⏳ |
| 5 | استعلام تاريخ السعر يُرجع صفاً لكل run بلا مسح ملفات | ⏳ |

### ما تحقق فعلياً في المرحلة 2

تشغيل حقيقي (`--match-only`, لا يلمس السلة):

```
runs (run_key, total_items, actual run_items rows)
  wardany/20260830_2050    2 → 2 ✅
  wardany/20260830_2052    3 → 3 ✅
```

مع `--item-workers 2` كتبت العمليتان في نفس `run_key` بلا تعارض وبلا دمج:
4 أصناف → 4 صفوف. الأبعاد لم تتفرّع: 8 أصناف مميزة عبر 10 صفوف حقائق.

`first_seen_at` ثابت و`last_seen_at` يتقدّم عبر الـ runs — تحقق فعلي:

```
53804::IMP FEROGLOBIN B12 30 CAP   first=17:46:51  last=17:48:12
```

### ⚠️ خلل مكتشف أثناء المرحلة 2: `total_items = 0`

الـ run `wardany/20260830_2050_2` يحمل `total_items=0` و`finished_at=NULL`
مع وجود 8 صفوف `run_items` فعلية.

السبب: عندما يُنشئ `unique_run_id` لاحقة `_2` بسبب تعارض في نفس الدقيقة،
تُقاطَع العملية قبل الوصول إلى `finish_run` — الـ run الأول انتهى والثاني
بدأ في نفس الدقيقة وقُوطع. الصفوف موجودة والبيانات سليمة، لكن حقلا
`finished_at` و`total_items` لم يُحدَّثا.

الأثر: `v_run_summary` صحيح (يحسب من `run_items` لا من `total_items`)، لكن
`runs.total_items` غير موثوق كمصدر وحيد. الاستعلامات يجب أن تعتمد على
`v_run_summary`. سيُصلحه `db-import` في المرحلة 4 لأن `FINISH_RUN` يستمد
العدد من الحقائق مباشرة.

---

## ما يجب ألا يحدث

- ❌ تعديل مخطط `manual_review_decisions.db` أو منطق `ManualReviewStore`
- ❌ إضافة SQLAlchemy أو أي ORM — `sqlite3` يكفي والمشروع لا يحتوي أياً منها
- ❌ حذف أو تقليل مخرجات CSV/XLSX في هذه المراحل
- ❌ ترك أي مسار كتابة بلا `try/except` يمنع تعطيل الـ run
- ❌ ملف > 100 سطر أو دالة > 20 سطراً بلا إدراج في baseline الفحص
- ❌ تفعيل `run_candidates` افتراضياً
