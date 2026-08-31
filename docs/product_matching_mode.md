# وضع مطابقة المنتجات (Product Matching Mode)

## التعريف

**Product Matching** هو وضع مستقل (`standalone`) بياخد ملف إكسل فيه أصناف
مخزون/طلب، ويطابق كل صنف مقابل **كتالوج Tawreed** (CSV متصدّر من قبل
`export-products`)، ويطلع ملف CSV فيه أفضل مرشّح (`matched_product_name_en`)،
درجة الثقة (`score`)، وحالات (`matched-only` / `not-orderable` / `no-results`).

> **الوضع ده مش بيحط حاجة في السلة.** هو خطوة فحص وتحضير قبل ما تنفذ طلب
> فعلي. الـ order بيستخدم نفس الـ pipeline جوّه، بس هنا بتديره لحاله.

---

## الفايدة — ليه تستخدمه؟

| الفايدة | الشرح |
|---|---|
| **تشغيل جاف (dry-run)** | تقدر تطابق 1000 صنف دفعة واحدة بدون ما تلمس سلة الصيدلية على Tawreed. |
| **فحص جودة المطابقة** | يشغّل نفس الـ `MatchPipeline` بتاع الـ order، فياريك النتايج (matched / not-orderable / no-results) قبل ما تاخد قرار. |
| **تدقيق الـ AI ranking** | لو عندك شك إن نموذج AI بيغلط، شغّل `match-products` على نفس ملف الإكسل وقارن النتائج يدوي قبل ما تستخدمه في أمر order. |
| **استخراج حالات المراجعة اليدوية** | الأصناف اللي confidence بتاعها ضعيف بتروح لملف `manual_review_*.csv/jsonl` يتفتح في تاب **Manual Review** في الـ GUI. |
| **بناء trace كامل** | مع `--trace`، كل قرار (fuzzy score / AI verdict / reason) بيتسجل في `artifacts/<profile>/match-products/<timestamp>/trace.log` — مفيد في تحليل الـ mismatches زي `METHYL_FOLATE_ORCHIDIA_MISMATCH_ANALYSIS.md`. |
| **Resume بعد انقطاع** | لو الشبكة قطعت أو عملت `Ctrl+C`، تقدر تكمل من عند ما وقفت بـ `--resume` أو `--start`/`--end`. |
| **بدون متصفح** | الـ mode ده لا يحتاج Playwright/Chromium — قراءة CSV + خوارزمية مطابقة + (اختياري) HTTP لـ AI فقط. |

---

## الـ CLI — `match-products`

### التسجيل

```bash
py run.py match-products --profile wardany \
  --excel data/input/inventory.xlsx \
  --tawreed-csv artifacts/wardany/tawreed_products.csv \
  --limit 50 \
  --trace
```

### الخيارات (من `cli_match_products.py` و `--help`)

| Flag | الوظيفة |
|---|---|
| `--config <path>` | مسار ملف الإعدادات (افتراضي `state/config.yaml`). |
| `--profile <key>` | اسم الـ profile في `config.yaml` (مثلاً `wardany`). |
| `--excel <path>` | ملف الإكسل اللي فيه الأصناف المراد مطابقتها (إلزامي). |
| `--tawreed-csv <path>` | كتالوج Tawreed (CSV) — لو مش موجود بيُحضَر تلقائيًا من أحدث تصدير تحت `artifacts/export-products/<profile>/*/tawreed_products*.csv`. |
| `--output <path>` | مكان حفظ CSV النتيجة (افتراضيًا run-scoped تحت `artifacts/<profile>/match-products/<ts>/`). |
| `--limit N` | عدد الأصناف المراد معالجتها (افتراضي 50 — لا نهائي لو `0`). |
| `--threshold T` | حد الـ fuzzy score لتقبيل المرشّح قبل تدخل الـ AI (من `MatchingConfig`). |
| `--start N` / `--end N` | نطاق الصفوف للمعالجة (مفيد للـ batch كبير). |
| `--resume` | يكمل من آخر `last_end` محفوظ في progress file. |
| `--trace` | يكتب `trace.log` بكل قرار مطابقة + سبب القبول/الرفض. |

### المخرجات

- CSV رئيسي: `<output>/match_products_<ts>.csv` فيه أعمدة زي:
  - `source_name` (اسم الصنف من الإكسل)
  - `matched_product_name_en` (أفضل مرشّح أو فاضي)
  - `score` (درجة fuzzy)
  - `ai_confidence` (لو الـ AI تكلّم)
  - `match_status` (`matched-only` / `not-orderable` / `no-results` / ...)
- ملفات المراجعة اليدوية: `manual_review_*.csv` و `manual_review_candidates_*.jsonl` لو في أصناف محتاجة قرار بشري.
- Trace log (لو `--trace`): `trace.log` بكل حدث.

### مثال كامل (PowerShell)

```powershell
py run.py match-products `
  --profile wardany `
  --excel data/input/order_items/SMALL_TEST.xlsx `
  --tawreed-csv artifacts/wardany/tawreed_products.csv `
  --limit 100 `
  --trace `
  --output artifacts/wardany/match-products/small_test.csv
```

---

## الـ GUI — تاب **Product Matching**

التبويب ده موجود في `src/ui/views/streamlit_product_matching.py` ومسجّل في
`streamlit_main.py` جنب **Order**, **Manual Review**, **Results**, ...

### الـ Form (اللي بيظهر للمستخدم)

| حقل | نوع | افتراضي | الوظيفة |
|---|---|---|---|
| **Excel source** | radio (Existing / Upload) | Existing | يختار ملف إكسل من `data/input/...` أو يرفع ملف جديد. |
| **Profile** | selectbox | أول profile في `config.yaml` | يحدد الـ profile المستخدم. |
| **Item limit** | number_input | `50` | الحد الأقصى للأصناف. |
| **Trace** | checkbox | `True` | يكتب الـ trace log أثناء التشغيل. |
| **Run Product Matching** | submit | — | يشغّل الـ subprocess. |

### الـ Flow اللي ورا الـ Submit

1. الـ GUI يبني CLI command مطابق تمامًا للأمر اللي فوق (`product_matching_command`).
2. يشغّله كـ **subprocess في الخلفية** (`start_cli_subprocess`) ويخزّن
   الـ handle في `st.session_state["product_matching_process"]`.
3. يعرض **حالة live**:
   - شريط warning "Product matching is running."
   - زرار "Refresh Matching Status" يعمل `st.rerun()` لتحديث الـ UI.
   - آخر 4000 حرف من اللوج في `st.code(...)`.
   - الجدول المباشر للـ CSV اللي بيتكتب (`render_matching_output_table`).
4. لما الـ process يخلص، يعرض:
   - نتيجة الـ subprocess (`ok` / `exit_code` / `command` / `error_message`).
   - الجدول النهائي كامل.
   - تنظيف `session_state`.

### فايدة الـ GUI بدل الـ CLI

| الميزة | الشرح |
|---|---|
| **بدون أوامر** | مش محتاج تفتح terminal — كله clicks. |
| **رفع ملف من المتصفح** | لو ملف الإكسل عندك على سطح المكتب، ارفعه بـ drag-drop بدل ما تنسخه للمسار. |
| **مراقبة لحظية** | شوف اللوج والجدول يتحدث live، اعمل refresh يدوي، ومعرفة exit code بدون ما تفتح shell. |
| **مشاركة سهلة** | السكرين ده بيتحفظ/يتصور لمديرك أو للـ QA بدون ما تشرح أوامر. |
| **Fallback للـ CLI** | لو الـ GUI علقت، الأمر نفسه متاح في الـ terminal — نفس النتيجة بالضبط. |

---

## علاقة الـ Product Matching بأوضاع تانية

```
                  ┌──────────────────────────┐
                  │  export-products (CLI)   │  → artifacts/<profile>/tawreed_products.csv
                  └────────────┬─────────────┘
                               │
                               ▼
   ┌─────────────────────── Product Matching ───────────────────────┐
   │  • CLI: match-products                                         │
   │  • GUI: Tab "Product Matching"                                 │
   │  • Output: match_products.csv + manual_review_*.csv + trace    │
   └─────────────┬─────────────────────────┬────────────────────────┘
                 │                         │
                 ▼                         ▼
   ┌─────────────────────┐     ┌──────────────────────────┐
   │ order --match-only  │     │ Tab "Manual Review" (GUI)│
   │ (داخل الـ order)    │     │ → قرار بشري للأصناف      │
   └─────────────────────┘     └──────────────────────────┘
                 │
                 ▼
       ┌─────────────────�
       │ order (تنفيذ)  │  → السلة + Checkout
       └─────────────────┘
```

---

## أمثلة استخدام حقيقية

### 1. قبل ما تنفذ طلب كبير لأول مرة

```bash
py run.py match-products --profile wardany \
  --excel data/input/new_pharmacy_inventory.xlsx \
  --tawreed-csv artifacts/wardany/tawreed_products.csv \
  --trace
```

→ شوف النتيجة: كام matched-only / not-orderable / no-results. لو فيه no-results كتير،
دخّل الـ manual review وقرّر الأصناف البديلة قبل ما تطلب.

### 2. مقارنة نماذج AI (workflow الاختبار)

شغّل `match-products` على نفس ملف الإكسل مع نماذج AI مختلفة عن طريق تعديل
`matching.ai_model` في `config.yaml`، وقارن الـ output CSV مع تقرير زي
`docs/matching_model_ranking.md`.

### 3. Resume بعد ما الـ subprocess اتقتل

```bash
py run.py match-products --profile wardany \
  --excel data/input/big_inventory.xlsx \
  --tawreed-csv artifacts/wardany/tawreed_products.csv \
  --resume --trace
```

### 4. Batch كبير بحدود

```bash
py run.py match-products --profile wardany \
  --excel data/input/big_inventory.xlsx \
  --tawreed-csv artifacts/wardany/tawreed_products.csv \
  --start 0 --end 500 --trace

py run.py match-products --profile wardany \
  --excel data/input/big_inventory.xlsx \
  --tawreed-csv artifacts/wardany/tawreed_products.csv \
  --start 500 --end 1000 --trace
```

---

## ملخص سريع

| | CLI | GUI |
|---|---|---|
| **اسم الأمر** | `py run.py match-products` | تاب "Product Matching" |
| **الـ use-case** | أتمتة، سكربتات، CI، سيرفر بدون واجهة | مستخدم عادي، مراجعة بصرية، رفع ملفات |
| **الـ output** | CSV + trace + manual_review | نفس الـ CSV + عرض dataframe مباشر |
| **يحتاج متصفح؟** | لا | لا (subprocess للـ CLI فقط) |
| **يعدّل السلة؟** | **لا** | **لا** |

> **القاعدة الذهبية:** لو عايز تطابق بس من غير ما تحرك حاجة في Tawreed →
> استخدم Product Matching (CLI أو GUI). لو عايز تطابق **وتحط في السلة** →
> استخدم `order --match-only` (CLI) أو تاب **Order** (GUI).

---

## مرجع الكود

- `src/cli/commands/cli_match_products.py` — تسجيل الأمر `match-products` وبناء الـ pipeline.
- `src/core/drug_matching/pipeline.py` — `MatchPipeline.run_full` (الـ core).
- `src/core/drug_matching/tracing.py` — `MatchTraceLog` (للـ `--trace`).
- `src/ui/views/streamlit_product_matching.py` — تاب الـ GUI والـ form والـ subprocess wrapper.
- `src/ui/streamlit_main.py` — تسجيل التبويب في الـ Streamlit app.
- `docs/drug_matching_algorithm_explained.html` — شرح بصري لخوارزمية المطابقة.
- `docs/matching_model_ranking.md` — مقارنة نماذج AI على ملف SMALL_TEST.xlsx.
