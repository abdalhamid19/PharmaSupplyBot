# 01 — الوضع الحالي: ما يُنتجه `order run` فعلياً

## مسار التنفيذ من الأمر إلى الملفات

```
run.py
  └─ src/cli/typer_app.py:324  order_cmd()          ← تعريف الخيارات
      └─ _run_registered(ctx, "order")              typer_app.py:127
          └─ src/cli/commands/cli_order.py:67       run_order_command()
              └─ execute_profiles()                 cli_order.py:189
                  └─ cli_order_execution.py:29      run_single_profile()
                      └─ artifact_run("order", profile_key)   ← ينشئ المجلد
                          └─ run_single_profile_items()        cli_order_execution.py:43
                              ├─ bot.match_items_only(items)   (match-only)
                              └─ bot.place_order_from_items(items)
```

لكل عنصر (item)، وبعد انتهاء معالجته، يُستدعى المسجِّل:

```
src/tawreed/order/tawreed_order_summary.py:236   record_order_run_artifacts()
  └─ tawreed_order_summary_build.py:16           append_order_item_artifacts()
      ├─ order_item_summary_row(...)             src/core/ordering/order_run_artifact_rows.py:61
      ├─ _append_item_summary_row()              → CSV + XLSX + TXT
      ├─ _append_final_trace_row()               → order_matching_trace CSV + TXT
      └─ _handle_manual_review_or_auto_save()    → manual_review CSV/TXT + JSONL
```

نقطة مهمة: **الكتابة تحدث صفاً بصف (append) في نهاية كل عنصر**، لا مرة
واحدة في نهاية الـ run. هذا يعني أن الكتابة إلى SQLite يمكن أن تتبع نفس
النمط دون تغيير في التصميم.

## مكان المخرجات

```
artifacts/order/<profile>/<run_id>/
```

`run_id` بدقة الدقيقة `%Y%m%d_%H%M` مع لاحقة `_2`, `_3`… عند التعارض
(`src/core/artifact_run.py:31-40`). مثال حقيقي من المستودع:

```
artifacts/order/wardany/20260830_1809/
    order_item_summary_20260830_1809.csv     12.8 KB
    order_item_summary_20260830_1809.xlsx    10.9 KB
    order_item_summary_20260830_1809.txt     31.3 KB
    order_matching_trace_20260830_1809.csv    5.3 KB
    match_only_summary_20260830_1809.csv    133.6 KB   ← الأثقل
    matching_trace_20260830_1809.csv         46.6 KB
```

## أعمدة `order_item_summary` — صف واحد لكل عنصر إدخال

39 عموداً، مُستخرَجة من رأس ملف حقيقي:

**هوية العنصر والنتيجة**
`item_code`, `item_name`, `item_qty`, `status`, `reason`,
`ordered_total_qty`, `matched_query`, `deterministic_score`, `matched`,
`deterministic_match_found`, `manual_review_blocked_match`,
`manual_review_required`

**المنتج المطابَق والفائز** (المصدر: `order_winner_fields.py:21-36`)
`matched_product_name_en`, `matched_product_name_ar`, `matched_product_id`,
`matched_store_product_id`, `winner_product_id`, `winner_store_product_id`,
`winner_available_quantity`, `winner_sale_price`, `winner_Purchase_Price`

**المخزن والخصم** (المصدر: `order_selected_fields.py:12`)
`selected_store_name`, `selected_discount_percent`, `tie_break_reason`
+ عند التقسيم على أكثر من مخزن تُضاف ديناميكياً:
`selected_store_name_N`, `selected_discount_percent_N`, `selected_qty_N`

**المراجعة اليدوية**
`manual_review_category`, `manual_review_reason_detail`,
`manual_review_blocking_phase`, `candidate_safety_reason`

**التوقيتات** (11 عموداً)
`elapsed_seconds`, `match_elapsed_seconds`, `api_context_init_seconds`,
`api_search_seconds`, `dom_wait_seconds`, `dialog_close_seconds`,
`manual_review_lookup_seconds`, `match_decision_seconds`,
`add_to_cart_seconds`, `artifact_write_seconds`, `summary_build_seconds`

### قيم `status` الممكنة
من `src/tawreed/tawreed_summary.py:122-156` و`order_run_artifact_rows.py:9`:

`added-to-cart`, `matched-only`, `no-results`, `matched-but-unavailable`,
`not-orderable`, `manual-review-required`, `manufacturer-mismatch`,
`skipped`, `failed`

## أعمدة `match_only_summary` — صف لكل **مرشّح**، لا لكل عنصر

61 عموداً. مهم لأن هذا هو الملف الوحيد الذي يحتوي على المرشحين المرفوضين
مع سبب الرفض. الأعمدة الجوهرية:

- نفس حقول العنصر (`item_code`, `item_name`, `status`, …)
- `candidate_rank`, `candidate_source` (`site_api` أو `dom_fallback`),
  `is_best_match`, `query`, `row_index`
- تفكيك الدرجة: `total_score`, `sequence_score`, `overlap_score`,
  `numeric_overlap`, `exact_bonus`, `availability_bonus`,
  `critical_penalty`, `extra_token_penalty`, `semantic_penalty`,
  `sort_key`, `accepted`, `accepted_reason`, `rejection_reason`
- حقول Tawreed الخام بادئة `api_`:
  `api_productId`, `api_storeProductId`, `api_productNameEn`,
  `api_productName`, `api_availableQuantity`, `api_productsCount`,
  `api_storeName`, `api_supplierName`, `api_companyName`,
  `api_discountPercent`, `api_retailPrice`, `api_salePrice`, `api_currency`,
  `api_priority`, `api_stockLevel`, `api_minOrderDiff`, `api_imageContentId`
- `api_raw_candidate_json` — الحمولة كاملة كنص JSON

### شكل حمولة Tawreed الحقيقية
من `api_raw_candidate_json` في run فعلي:

```json
{
  "productId": 2505,
  "storeProductId": 2902379,
  "productName": "كال ماج 30 اقراص",
  "productNameEn": "CAL MAG 30 F.C. TABLETS",
  "storeName": "شركه العاصمه (الجيزه)",
  "companyName": "شركه العاصمه (الجيزه)",
  "availableQuantity": 1,
  "productsCount": 22,
  "retailPrice": 147.0,
  "salePrice": 116.13,
  "discountPercent": 21.0,
  "currency": "ج.م",
  "priority": 10,
  "stockLevel": 0,
  "minOrderDiff": null,
  "imageContentId": "2505_5"
}
```

`productsCount: 22` يعني أن هذا المنتج متوفر في 22 مخزناً. هذا هو الرقم
الذي يشغّل نافذة المخازن، وهذه المخازن الـ 22 هي البيانات التي لا تُحفظ.

## قاعدة البيانات الموجودة أصلاً

المشروع يستخدم SQLite بالفعل:

```
src/core/database/
    database.py              DatabaseManager + get_db_manager() (كاش بالمسار)
    database_pool.py         DatabasePool — اتصال قصير العمر، WAL، RLock
    database_queries.py      execute_query / execute_update / test_connection
    database_credentials.py  حلّ المسار: وسيط → env → افتراضي
```

الافتراضي: `state/manual_review_decisions.db` (327 KB حالياً في المستودع).
المستخدِم الوحيد: `src/core/manual_review/manual_review_store.py` بجدول
واحد `manual_review_decisions`.

خصائص جاهزة للاستفادة منها:
- `PRAGMA journal_mode=WAL` مفعّل في `database_pool.py:30` — يسمح بقارئ
  متزامن مع كاتب، مهم لأن Streamlit قد يقرأ أثناء الـ run.
- `timeout=30.0` في `sqlite3.connect` — يعالج `database is locked` عند
  التزامن.
- `check_same_thread=False` + `threading.RLock` — آمن للخيوط، **لكن ليس
  للعمليات** (انظر `04_write_strategy.md`).
- نمط `_init_schema_once` + `_ensure_column` لترقية المخطط تدريجياً.

## البيئة

- Python 3.11.15 في `.venv`، SQLite 3.53.1 (يدعم `WITHOUT ROWID`،
  `UPSERT`، `generated columns`، `STRICT` tables)
- لا ORM. `sqlite3` المدمج فقط. `requirements.txt` لا يحتوي SQLAlchemy.
- `pandas>=2.2`, `openpyxl>=3.1`, `typer>=0.12`, `streamlit>=1.44`
- `state/` مُستثنى من git بالكامل (`.gitignore`) → قاعدة البيانات لن
  تُرفَع، وهذا مطلوب.

## القيود التي يفرضها المشروع على الكود الجديد

من `docs/project_guidelines.md` و`tools/rule_audit.py`:

- حد أقصى 100 حرف للسطر
- حد أقصى 100 سطر للملف، 20 سطراً للدالة (يُفحص بـ `tools/rule_audit.py`)
- docstring إلزامي للوحدات والدوال والأصناف العامة
- فصل منطق العمل عن Playwright/CLI/Streamlit
- استيراد نسبي داخل `src/`
- `state/` للحالة الدائمة، `artifacts/` للمخرجات القابلة للحذف
  → **قاعدة البيانات تنتمي إلى `state/`، والقرار المتفق عليه يحترم ذلك**
