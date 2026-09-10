# تحليل read-only للـ full replay ومقاييس candidate coverage

## الخلاصة التنفيذية

هذا تقرير تحليل مستقل للنسخة الحالية. لم أشغّل replay جديدًا، ولم أعدّل كود
الإنتاج أو `state` أو أي input. قرأت artifacts الموجودة، وراجعت مسار إنشاء
المرشحين وكتابتها وعرضها.

النتيجة الأساسية: لا يجوز اعتبار الرقم `2397` مقامًا صالحًا تلقائيًا للنسب
المستخرجة من artifacts الحالية. وثيقة baseline تسجل `total_items=2397` للـrun
`wardany/20260909_1457`، لكن `order_item_summary` لذلك الـrun يحتوي 799 صفًا فقط،
وكل target summary يحتوي 799 صفًا. كما أن ملف الإدخال الموجود حاليًا يحتوي 961
صف بيانات عند قراءته read-only. لذلك يجب أولًا تثبيت تعريف item ومصدر المقام:
صف إدخال، كود فريد، item بعد التجميع، أو وحدة كمية.

العداد الحالي الأكثر موثوقية من artifacts هو:

```text
C_union_observed = candidate_count_total
C_saved          = عدد options المحفوظة في JSONL
C_display        = عدد options التي تعرضها واجهة Manual Review بعد display limit
```

أما `C_identity` و`C_discovery` فلا يمكن استخراج عددهما generated بدقة من
JSONL الحالي؛ فالـJSONL يحفظ union النهائي بعد dedup/ranking، ولا يحفظ كل مصدر
قناة قبل الدمج. يمكن استخراج `C_identity_retained` و`C_discovery_retained`
كتقدير موثق من `candidate_method`، لكن يجب عدم تسميتهما generated coverage.

## نطاق القراءة وحدودها

- التحليل read-only فقط؛ لم أكتب إلى SQLite، ولم أشغّل matcher على input أو
  target workbook، ولم أنشئ replay جديدًا.
- الـfull historical artifacts المتاحة هي `20260909_1457`، وتحتوي 799 صف
  summary لكل target.
- `20260910_1145` و`20260910_1233` هما replay محدود لـ100 صفًا؛ الأخير هو
  replay بعد phase 2 bounded candidate coverage.
- كل target حُلل مستقلًا. لا ينبغي جمع صفوف Baraka وQaysar باعتبارها rows
  واحدة؛ `target_key` جزء من هوية المرشح.
- `candidate_count_total` هو عدد المرشحين الناتج بعد قنوات identity/discovery
  الحالية، وdedup، وranking، وقبل save slice. ليس عدد كل صفوف catalog التي كان
  يمكن فحصها لو أزيلت حدود discovery.

## ما الذي تقوله artifacts المتاحة؟

### Baseline full: `20260909_1457`

| target | summary rows | manual-review rows | `C_identity_retained` | `C_discovery_retained` | `C_union` sum | `C_saved` sum | `C_display` sum، default=5 | union p50/p95/p99/max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| البركة شركات | 799 | 115 | 154 | 1 | 155 | 155 | 155 | 0 / 1 / 2 / 4 |
| القيصر شركات | 799 | 117 | 154 | 0 | 154 | 154 | 154 | 0 / 1 / 2 / 3 |

هذه أعداد options/rows المرشحة، وليست precision أو recall. في Baraka كان هناك
مرشح retained واحد من `arabic_fuzzy`، بينما بقية options retained جاءت من
identity-derived methods. في Qaysar لم يظهر discovery-derived option في
artifact النهائي.

### Replay الحالي المحدود بعد phase 2: `20260910_1233`

| target | summary rows | manual-review rows | `C_identity_retained` | `C_discovery_retained` | `C_union` sum | `C_saved` sum | `C_display` sum، default=5 | union p50/p95/p99/max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| البركة شركات | 100 | 7 | 8 | 0 | 8 | 8 | 8 | 0 / 1 / 1 / 2 |
| القيصر شركات | 100 | 16 | 26 | 0 | 26 | 26 | 26 | 0 / 2 / 3 / 4 |

في هذا replay كل options الجديدة تقريبًا ناتجة عن
`review_identity`/`review_identity_prefix`، وليس عن توسيع fuzzy أو cross-language
discovery. وهذا يثبت زيادة coverage signal فقط، ولا يثبت precision.

للمقارنة داخل العينة نفسها:

| target | قبل phase 2، `20260910_1145` manual review | بعد phase 2 manual review | تغير `C_union` sum |
|---|---:|---:|---:|
| البركة شركات | 0 | 7 | 0 → 8 |
| القيصر شركات | 6 | 16 | 10 → 26 |

### ملاحظة عن `order/wardany`

`artifacts/order/wardany` و`artifacts/excel-target` ليسا نفس القياس:

- `order_item_summary_*.csv` يصف نتيجة order العامة، و
  `manual_review_required` فيه مبني على status وقرارات manual review العامة.
- `match_only_summary_<target>.csv` يصف نتيجة target محدد، وفيه
  `manual_review_required` target-scoped.
- لذلك لا يجوز جمع manual-review count في order مع manual-review count في
  Baraka/Qaysar أو اعتباره double-count-free إلا بعد join صريح بالمفتاح
  `(item_code, item_name, target_key, source_kind)`.

## Schema ومصادر العدادات

### Target summary CSV

الحقول الحالية المهمة هي:

```text
item_code, item_name, status,
identity_evidence_kind, identity_evidence,
compatibility_status, compatibility_rejection,
candidate_count_total, candidate_count,
manual_review_required, manual_review_category,
candidate_source_file, matching_source, matching_source_label
```

في `cli_order_excel_target.py` يحصل التسلسل التالي:

1. `all_review_candidates = tuple(result.review_candidates)`.
2. `review_candidates = all_review_candidates[:review_limit]`.
3. `candidate_count_total = len(all_review_candidates)`.
4. `candidate_count = len(review_candidates)`.
5. `manual_review_required = candidate_count_total > 0`.

إذًا `candidate_count` في target summary هو العدد الذي مر إلى writer بعد
save limit، وليس universe الكامل. الملف لا يحتوي حقلًا اسمه
`candidate_count_saved` في هذا summary؛ لذلك لا ينبغي أن يستنتج report هذا
الحقل من header غير الموجود.

### Target manual-review CSV

هذا الملف لا يحتوي إلا الصفوف التي دخلت queue، ويضيف:

```text
candidate_count,
candidate_count_total,
candidate_count_saved,
identity_evidence_kind,
candidate_compatibility_status,
target_key, source_file, reason
```

المصدر الموثوق لـ`C_saved` في target artifact هو `candidate_count_saved` هنا
أو عدد `options` في envelope المقابل في JSONL. يجب أن يتحقق التقرير من:

```text
candidate_count_total >= candidate_count_saved >= 0
candidate_count_saved == len(options)
```

### Candidate JSONL

كل envelope يحتوي item identity، target/source provenance، ثم:

```text
candidate_count_total,
candidate_count_saved,
options[]
```

وكل option جديد يحمل، عند توفره:

```text
candidate_method,
identity_evidence_kind,
ranking_tier,
target_key,
source_file,
excel_target_row_key,
excel_target_source_row,
compatibility_status,
compatibility_rejection,
score_margin,
shared_brand_tokens
```

هذه هي أفضل مادة read-only لمعرفة ما حُفظ فعلًا، لكنها لا تسجل options التي
دخلت قناة ثم أزيلت عند union dedup، ولا المصدرين إذا فاز أحدهما على الآخر لنفس
`excel_target_row_key`.

### Order artifacts

يجب قياس `order_item_summary_*.csv` على حدة باستخدام:

```text
N_order_summary_rows
N_order_manual_review_required
status distribution
manual_review_category distribution
match_elapsed_seconds / match_elapsed_ms percentiles
```

لا تُستخدم هذه الحقول لاستنتاج `C_identity` أو `C_discovery` الخاصة بـExcel
target؛ مسار order العام لا يحفظ نفس target-scoped candidate envelope.

## التعريف الدقيق المقترح لمقاييس C

ليكن `i` item، و`t` target، وليكن مفتاح row المستقر:

```text
row_key = excel_target_row_key(target_key, source_file,
                               source_row_number, store_product_id, name)
```

### `C_identity`

```text
I(i,t) = unique row_key produced by:
         identity_index.identify(i)
         ∪ identity_index.identify_review_candidates(i)
C_identity(i,t) = |I(i,t)|
```

هذا يشمل identity evidence الموثوق وreview-only identity، لكن يجب الاحتفاظ
بـ`identity_plane` و`review_only` كـsub-breakdown حتى لا يبدو أن الاثنين يسمحان
بالـautomatic match.

### `C_discovery`

```text
D(i,t) = unique row_key produced by target-scoped review discovery
         and catalog-resolved diagnostic candidates
C_discovery(i,t) = |D(i,t)|
```

يشمل `ReviewDiscoveryHit` وdiagnostics التي حُلّت إلى صف فعلي في catalog. يجب
تسجيل `channel=english_fuzzy` أو `arabic_fuzzy`، لأن `candidate_method` الحالي
قد يحمل نفس label لمصدر discovery وdiagnostic.

### `C_union`

```text
C_union(i,t) = |I(i,t) ∪ D(i,t)|
C_overlap(i,t) = |I(i,t) ∩ D(i,t)|
```

هذا هو العدد الذي يجب أن يقود `manual_review_required` في target path. في
artifact الحالي أقرب حقل له هو `candidate_count_total`، مع تسمية صريحة:

```text
C_union_observed = candidate_count_total
```

ولا نسمّيه exhaustive universe إلا إذا كان retrieval/discovery نفسه exhaustive
أو صدر معه `catalog_scan_count` و`retrieval_truncated=false`.

### `C_saved`

```text
C_saved(i,t) = عدد options في JSONL envelope بعد save limit
```

يجب أن يساوي `candidate_count_saved` في manual-review CSV/envelope، وأن يطابق
`candidate_count` في target summary لنفس الصف.

### `C_display`

```text
C_display(i,t, d) = عدد options التي تعرضها UI بعد display limit d
```

عند target واحد ومصدر واحد فقط:

```text
C_display = min(C_saved, d)
```

لكن واجهة Streamlit تطبق `_limit_candidates_by_source` بعد دمج sources، وتحاول
الإبقاء على option من كل source عندما يكون ذلك ممكنًا. لذلك في run متعدد
targets يجب حساب `C_display` من options المدمجة، لا من جمع display counts لكل
target. القيمة default الحالية هي 5، مع إمكانية إضافة options من UI.

### Coverage وrecall وprecision

لأي مجموعة eligible ثابتة `E`:

```text
candidate_coverage = count(C_union > 0) / count(E)
manual_review_rate  = count(manual_review_required=True) / count(E)
```

يجب أن يتساويا في target summary عندما تكون rows `no-results`، مع تسجيل أي
استثناءات منفصلة.

الـrecall الحقيقي يحتاج gold row key `G(i,t)`:

```text
recall@all = count((G ∩ U) != ∅) / count(G is known)
recall@k   = count(G appears in first k ranked options) / count(G is known)
```

والـprecision يحتاج label بشريًا لكل option:

```text
precision@k = relevant options in first k / all options inspected in first k
```

لا يجوز اعتبار `manual_review_required=True` أو وجود candidate دليلًا على
precision، ولا اعتبار زيادة `C_union` recallًا إلا بعد وجود gold positives.

## ما الذي يجب أن يخرجه report read-only؟

يقترح التقرير read-only الأقسام التالية لكل `run_id` ولكل `target_key`:

1. **Run manifest**: `run_id`, profile، expected input count، summary row count،
   source paths، config limits، وhash/metadata إن كانت متاحة، مع flag صريح لأي
   denominator mismatch.
2. **Inventory**: عدد summary rows، عدد target manual-review rows، عدد JSONL
   envelopes، وعدد options، مع مقارنة CSV ↔ JSONL.
3. **Cardinality table** لكل target: مجموع ومتوسط وp50/p95/p99/max لكل من
   `C_identity_generated`, `C_discovery_generated`, `C_union_observed`,
   `C_saved`, و`C_display`.
4. **Channel breakdown**: counts حسب `candidate_method`, evidence kind،
   `ranking_tier`, compatibility status، review status، وsource file.
5. **Coverage table**: `identity_absent`, `identity_compatible`,
   `identity_variant_rejected`, `excel_target_candidate_available`، وmanual
   review rate.
6. **Integrity gates**: monotonicity، unique row keys، target/source provenance،
   equality بين CSV وJSONL، deterministic ordering، وعدم ظهور review-only
   evidence كـautomatic best match.
7. **Precision sample**: عينات positive/near-negative مع `item_key`, target row
   key، rank، method، reason، وhuman label. إذا لم توجد labels يكتب report
   `precision=not measured` بدل التخمين.
8. **Order-vs-target reconciliation**: يعرض order counts وtarget counts في
   جدولين منفصلين، ثم يوضح صراحة ما إذا كان join كاملًا أم لا.

صيغة CLI مقترحة، دون أن ينشئ report الحالي أي ملف جديد:

```powershell
python tools/report_excel_target_candidate_coverage.py `
  --run-dir artifacts/order/wardany/20260909_1457 `
  --target-root artifacts/excel-target `
  --expected-items 2397 `
  --display-limit 5 `
  --format markdown `
  --output -
```

السلوك الآمن للـtool: قراءة CSV/JSONL فقط، وعدم استدعاء live translation أو
browser/API أو `ManualReviewStore.upsert`، وعدم الكتابة إلى input أو state أو
artifacts. إذا احتاج حساب `C_identity_generated` و`C_discovery_generated` إلى
replay in-memory، يجب أن يكون ذلك opt-in، offline، مع `use_saved_approvals=False`
و`allow_live_translation=False`، وأن يخرج counters إلى stdout فقط.

## تعريف percentiles وقواعد المقارنة

تُحسب percentiles على **قيمة كل item**، وليس على flattened options. يجب تثبيت
طريقة واحدة في report؛ المقترح هو nearest-rank:

```text
percentile(q) = sorted_values[ceil(q*N) - 1]
```

ويُعرض دائمًا:

```text
p50, p95, p99, max
```

لكل من `C_identity`, `C_discovery`, `C_union`, `C_saved`, `C_display`، ولكل
target، مع `N` المستخدم في الحساب. القيم الحالية الموثقة أعلاه محسوبة على
per-row `candidate_count_total`، لا على 2397 المفترض.

بوابة المقارنة المقترحة للـfull replay القادم:

- لا تُقارن النسب قبل حل `N_expected` مقابل `N_summary`.
- لا يُقبل `C_saved > C_union` أو `C_display > C_saved`.
- يجب ألا يزيد `C_union` p99/max بسبب save/display setting وحده؛ إذا زاد، فذلك
  retrieval change يحتاج تفسيرًا مستقلًا.
- أي زيادة في manual-review coverage تُراجع مع precision sample وnear-negative
  gold، ولا تعتمد على العدد وحده.
- يجب أن تبقى `review_identity`, `review_identity_prefix`, `review_fuzzy` في
  review plane فقط، ولا تظهر كـautomatic verified match.

## الخلاصة القصيرة

الـartifacts تثبت أن الإصلاح الحالي زاد المرشحين في العينة المحدودة، خصوصًا
لـBaraka/Qaysar، وأن الزيادة جاءت من anchored review identity. لكنها لا تثبت
نتيجة full 2397 ولا precision. قبل أي threshold أو transliteration expansion،
يجب توحيد مقام full replay، وإضافة channel provenance لحساب
`C_identity_generated` و`C_discovery_generated`، ثم تشغيل التقرير read-only
على replay كامل ومراجعة gold positives وnear-negatives.

## مسارات الملفات التي قُرئت

### Artifacts

- `artifacts/order/wardany/20260909_1457/order_item_summary_20260909_1457.csv`
- `artifacts/order/wardany/20260909_1457/manual_review_20260909_1457.csv`
- `artifacts/order/wardany/20260909_1457/matching_trace_20260909_1457.csv`
- `artifacts/order/wardany/20260910_1145/order_item_summary_20260910_1145.csv`
- `artifacts/order/wardany/20260910_1233/order_item_summary_20260910_1233.csv`
- `artifacts/order/wardany/20260910_1233/manual_review_20260910_1233.csv`
- `artifacts/excel-target/البركة شركات/20260909_1457/` وكل من summary CSV وmanual-review CSV وcandidate JSONL داخله
- `artifacts/excel-target/القيصر شركات/20260909_1457/` وكل من summary CSV وmanual-review CSV وcandidate JSONL داخله
- `artifacts/excel-target/البركة شركات/20260910_1145/` و`20260910_1233/` للملفات نفسها
- `artifacts/excel-target/القيصر شركات/20260910_1145/` و`20260910_1233/` للملفات نفسها

### Code وdocs الخاصة بالـschema

- `src/cli/commands/cli_order_excel_target.py`
- `src/core/excel_target/excel_target_matching.py`
- `src/core/excel_target/excel_target_identity.py`
- `src/core/excel_target/excel_target_review_candidates.py`
- `src/core/excel_target/excel_target_review_discovery.py`
- `src/core/manual_review/manual_review_candidate_store.py`
- `src/core/manual_review/manual_review_candidates.py`
- `src/ui/manual_review/streamlit_manual_review_page.py`
- `docs/approved-manual-match-learning-20260909/07-baseline-data-analysis.md`
- `docs/approved-manual-match-learning-20260909/08-test-and-metrics-strategy.md`
- `docs/approved-manual-match-learning-20260909/16-phase2-candidate-coverage-plan.md`
- `docs/approved-manual-match-learning-20260909/17-phase2-replay-results.md`

### Input/config read-only sanity checks

- `data/input/order_items/09092026.xlsx`
- `state/config.yaml`
