# 03 — نقاط الالتقاط في الكود

## المشكلة الأساسية

الجداول الستة تحتاج بيانات موجودة في أماكن مختلفة من الكود، **وليست كلها
متاحة في نفس اللحظة**. الأصعب هو `run_item_stores` لأن بيانات كل المخازن
تُجلب ثم تُرمى.

## ما هو متاح اليوم وما ليس متاحاً

| الجدول | البيانات متاحة؟ | من أين |
|---|---|---|
| `runs` | ✅ | `artifact_run()` + `args` + `app_config` |
| `items` | ✅ | كائن `Item` |
| `run_items` | ✅ | `order_item_summary_row()` كما هو |
| `products` | ✅ | `decision.best_match.data` و diagnostics |
| `stores` | ⚠️ جزئياً | المُختار فقط. الباقي يحتاج التقاطاً جديداً |
| `run_item_stores` | ❌ | **لا يوجد. يحتاج hook جديد** |
| `run_candidates` | ✅ | `decision.diagnostics` |

## أين تُجلب بيانات كل المخازن وتُرمى

### مسار المتصفح
`src/tawreed/products/tawreed_products_flow.py`

```python
# السطر 224 — هنا تصل البيانات كاملة
def open_stores_dialog(bot, page, row) -> list[dict[str, Any]]:
    with page.expect_response(re.compile(f".*{STORE_DETAILS_ENDPOINT}.*")) as resp:
        stores_button(row).click()
        return stores_from_payload(resp.value.json())   # ← قائمة كل المخازن

# السطر 161 — هنا تُستهلك
def add_item_from_store_dialogs(bot, page, row, item):
    store_rows = open_stores_dialog(bot, page, row)     # ← كل المخازن
    while rem > 0:
        choice = _next_store_choice(bot, page, store_rows, used_ids, sels)
        sels.append((choice.store, ordered))            # ← المُختار فقط يُحفظ
    _record_stores(bot, sels)   # ← store_rows تُرمى هنا نهائياً
```

### مسار API
`src/tawreed/api/tawreed_api_flow_multistore.py:14`

```python
store_rows = api.get_store_details(match.data.get("productId") or match.data.get("id"))
```

نفس النمط: تُجلب، تُستهلك في الحلقة، تُرمى.

### مسار match-only
`src/tawreed/products/tawreed_match_only_metadata.py:35` و
`src/tawreed/api/tawreed_api_match_only_metadata.py:31`

```python
def match_only_store_rows(bot, page, match, active_query):
    row = matched_product_row(bot, page, match, active_query)
    return open_stores_dialog(bot, page, row)   # ← نفس البيانات مرة أخرى
```

## الحل: hook واحد للالتقاط

أربع دوال مختلفة تُنتج نفس النوع من البيانات (`list[dict]` لصفوف المخازن).
الحل ليس تعديل الأربع، بل **تخزين النتيجة على كائن `bot`** مثل ما يفعله
الكود أصلاً في `record_selected_stores()`
(`src/tawreed/store/tawreed_store_summary.py:11`)، ثم قراءتها من نقطة
واحدة عند كتابة الـ artifacts.

### الملف الجديد: `src/tawreed/store/tawreed_store_snapshot.py`

```python
"""Per-item store snapshot capture for order-run persistence."""

from __future__ import annotations

from typing import Any


def record_store_rows(bot, rows: list[dict[str, Any]], source: str) -> None:
    """Store all offering-store rows for the active item on the bot."""
    bot.last_store_rows = list(rows or [])
    bot.last_store_rows_source = source


def clear_store_rows(bot) -> None:
    """Reset captured store rows before the next item is processed."""
    bot.last_store_rows = []
    bot.last_store_rows_source = ""
```

### التعديلات المطلوبة (سطر واحد لكل موقع)

| الملف | السطر | التعديل |
|---|---|---|
| `products/tawreed_products_flow.py` | 231 | `record_store_rows(bot, rows, "store_details")` قبل `return` |
| `api/tawreed_api_flow_multistore.py` | 14 | نفس الشيء بعد `get_store_details` |
| `api/tawreed_api_match_only_metadata.py` | 31 | نفس الشيء |
| `tawreed_bot_core.py` | 73 | `clear_store_rows(self)` داخل `_reset_last_item_state()` |

`_reset_last_item_state()` يُستدعى قبل كل عنصر أصلاً — وهو المكان الصحيح
تماماً لأنه يضمن عدم تسرّب مخازن العنصر السابق إلى العنصر التالي.

### حالة الصنف أحادي المخزن

عندما `productsCount == 0` لا تُفتح نافذة المخازن على الإطلاق
(`tawreed_products_flow.py:145`, `tawreed_match_only_metadata.py:18`).
في هذه الحالة المخزن الوحيد موجود في `match.data` نفسه، فتُبنى قائمة من
عنصر واحد:

```python
if not bot.last_store_rows and match:
    record_store_rows(bot, [match.data], "search")
```

هذا الاحتياط ضروري وإلا فقدت كل الأصناف أحادية المخزن من
`run_item_stores`.

## نقطة الكتابة الرئيسية

الكتابة إلى SQLite تنتمي إلى **نفس المكان** الذي يكتب فيه CSV اليوم:

`src/tawreed/order/tawreed_order_summary_build.py:16`

```python
def append_order_item_artifacts(
    profile_key, item, summary, decision, label_suffix=None, matching_config=None
) -> None:
    """Append one item summary row and optional manual-review row."""
    row = order_item_summary_row(item, summary, decision, matching_config)
    _append_item_summary_row(profile_key, row, label_suffix)
    _append_final_trace_row(profile_key, row, label_suffix)
    _handle_manual_review_or_auto_save(...)
    # ↓ الإضافة الجديدة — سطر واحد
    _persist_run_item_to_db(profile_key, item, summary, decision, row)
```

**لماذا هنا؟**
- تُستدعى مرة واحدة لكل عنصر، في كل الأوضاع (order, match-only, api,
  browser) — أُثبت ذلك بأن `record_order_run_artifacts()`
  (`tawreed_order_summary.py:236`) هو المسار الوحيد الذي يصل إليها من
  كل من `record_item_summary` و`record_match_only_summary`.
- `row` المبنية أصلاً تحمل معظم حقول `run_items`. لا داعي لإعادة الحساب.
- تحترم قاعدة المشروع «Persist artifacts incrementally» بدلاً من تجميع
  كل شيء في الذاكرة حتى نهاية الـ run.

`_persist_run_item_to_db` يجب أن تكون **دالة تفويض نحيفة** في وحدة
منفصلة، لا منطقاً داخل ملف الـ artifacts:

```
src/core/database/order_runs_writer.py   ← منطق الكتابة
src/core/database/order_runs_rows.py     ← تحويل الكائنات إلى صفوف
src/core/database/order_runs_schema.py   ← DDL
src/core/database/order_runs_store.py    ← الواجهة العامة (Store class)
```

يحترم هذا حد الـ 100 سطر للملف وقاعدة فصل منطق العمل عن طبقة التكامل.

## بداية ونهاية الـ run

### الإدراج في `runs`

`src/cli/commands/cli_order_execution.py:38`

```python
with artifact_run("order", profile_key) as run:
    logger.info("artifact run started", ...)
    # ↓ إضافة
    open_run_record(run, app_config, args)
    run_single_profile_items(app_config, profile_key, profile, args)
```

هنا تتوفر كل بيانات الـ run: `run.run_id`, `run.profile_key`,
`run.directory`, و`args` بكل الخيارات، و`app_config` بإعدادات المخازن.

### التحديث النهائي

نفس الموقع، عند الخروج من `with`:

```python
finish_run_record(run.run_key)   # يضبط finished_at و total_items
```

يجب أن يكون داخل `try/finally` حتى يُسجَّل الـ run كمنتهٍ حتى عند الفشل —
وإلا سيبدو كل run فاشل كأنه لا يزال يعمل.

## الوضع الحرج: `item_workers > 1`

عندما `item_workers > 1` يتحول التنفيذ إلى `multiprocessing` بسياق
`spawn` (`cli_order_execution.py:130`). كل عامل عملية منفصلة:

```python
ctx = multiprocessing.get_context("spawn")
with ctx.Pool(processes=len(chunks)) as pool:
    return pool.map(run_order_chunk, payloads)
```

النتائج:
- `threading.RLock` في `DatabasePool` **لا يحمي** بين العمليات
- كل عامل يجب أن يفتح اتصاله الخاص — وهذا ما يحدث فعلاً لأن
  `get_connection()` قصير العمر
- `artifact_run_id` يُمرَّر في الـ payload (`item_worker.py:139`) فيعرف
  كل عامل `run_key` الصحيح

الحل مشروح في `04_write_strategy.md`. باختصار: WAL + `busy_timeout` +
معاملة قصيرة لكل عنصر + `UPSERT`. لا يحتاج قفلاً على مستوى التطبيق.

## خريطة التعديلات الكاملة

**ملفات جديدة** (كلها ≤ 100 سطر):
```
src/core/database/order_runs_schema.py     DDL + الترقيات
src/core/database/order_runs_store.py      OrderRunsStore
src/core/database/order_runs_writer.py     الإدراج/الترقية
src/core/database/order_runs_rows.py       التحويل من الكائنات إلى صفوف
src/core/database/order_runs_queries.py    استعلامات جاهزة للقراءة
src/tawreed/store/tawreed_store_snapshot.py  التقاط صفوف المخازن
src/cli/commands/cli_db_import.py          أمر db-import
src/core/ordering/store_identity.py        store_identity_key()
```

**ملفات مُعدَّلة** (تعديلات صغيرة جداً):
```
src/tawreed/products/tawreed_products_flow.py         +1 سطر
src/tawreed/api/tawreed_api_flow_multistore.py        +1 سطر
src/tawreed/api/tawreed_api_match_only_metadata.py    +1 سطر
src/tawreed/tawreed_bot_core.py                       +1 سطر
src/tawreed/order/tawreed_order_summary_build.py      +1 سطر
src/cli/commands/cli_order_execution.py               +2 سطر
src/cli/typer_app.py                                  أمر db-import
src/cli/cli_commands.py                               تسجيل الأمر
src/core/config/config_models.py                      DatabaseConfig
src/core/config/config_factory.py                     build_database_config
state/config.yaml                                     قسم database
```

مجموع التعديلات على الكود القائم: **~8 أسطر**. باقي العمل كله في ملفات
جديدة معزولة. هذا مؤشر جيد على أن نقاط الالتقاط صحيحة.
