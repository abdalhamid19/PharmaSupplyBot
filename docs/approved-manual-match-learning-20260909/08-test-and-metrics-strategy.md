# استراتيجية الاختبار والقياس لتحسين مرشحي المراجعة اليدوية

## 1. الغرض والنطاق

هذه وثيقة قياس قبل/بعد، وليست خطة إصلاح ولا تفويضًا لتعديل كود الإنتاج. هدفها
الإجابة عن السؤال التالي بطريقة قابلة لإعادة التشغيل:

> هل أصبح النظام يعرض المرشح الصحيح في حالات `manual review` الخاصة بـ Excel
> target، مثل `VOLTAREN 3AMP` و`زيثرون 3قرص س جديد`، مع بقاء المرشحين غير
> الصحيحين محدودين، والنتائج deterministic، والأداء وملفات النتائج وسلوك النظام
> السابقين سليمين؟

يشمل القياس:

1. استرجاع المرشح الصحيح `candidate recall`، وليس مجرد زيادة عدد المرشحين.
2. ضبط اتساع قائمة المرشحين، خصوصًا مرشحي نفس الاسم مع قوة/شكل/عبوة مختلفة.
3. ثبات الترتيب والنتيجة بين الإعادات وبين `item-workers` مختلفة.
4. زمن بناء الفهرس وزمن المطابقة وذيل الأداء.
5. عدم تغيير المطابقات الصحيحة السابقة أو دلالة flags الحالية.
6. سلامة provenance وملفات CSV/JSONL وقواعد SQLite وعدم خلط Excel target مع Tawreed.

لا يُقبل أي استنتاج من تشغيل واحد غير مرتبط بـ commit، أو من عدد `matched`
وحده، أو من نجاح manual override محفوظ سابقًا.

## 2. مصادر الفحص الحالية

المصادر الأولية التي بُنيت عليها هذه الاستراتيجية هي كود المستودع واختباراته
وأدواته، لا ملخصات خارجية:

| المجال | المصدر الموجود | ما يثبته حاليًا |
|---|---|---|
| اكتشاف المرشحين | [`excel_target_review_discovery.py`](../../src/core/excel_target/excel_target_review_discovery.py) | مسار fuzzy منفصل للإنجليزي والعربي، thresholds، حد `limit`، وترتيب deterministic. |
| تحويل المرشح إلى artifact | [`excel_target_review_candidates.py`](../../src/core/excel_target/excel_target_review_candidates.py) | المرشح يجب أن يكون صفًا من الكتالوج المحمّل، مع compatibility وrow key وprovenance. |
| قرار المطابقة | [`excel_target_matching.py`](../../src/core/excel_target/excel_target_matching.py) | التحقق من identity ثم compatibility، وحماية `use_saved_approvals=False` للمقارنة counterfactual. |
| تشغيل Excel target | [`cli_order_excel_target.py`](../../src/cli/commands/cli_order_excel_target.py) | حقول summary، `candidate_count_total`، `candidate_count`، ملفات manual review، والحد الزمني 300 ثانية. |
| تقييم offline | [`baraka_coverage_report.py`](../../scripts/baraka_coverage_report.py) | تصنيف identity/variant/candidate/absent، مع total/saved candidates. |
| مقارنة before/after | [`evaluate_excel_target.py`](../../scripts/evaluate_excel_target.py) | matched set، تغيّر حالات المراجعة، gold labels، data-quality errors، وsafety errors. |
| benchmark | [`baraka_index_benchmark.py`](../../scripts/baraka_index_benchmark.py) | زمن بناء الفهرس، زمن المطابقة الكلي والمتوسط، وعدد المطابقات. |
| اختبارات discovery | [`test_excel_target_review_discovery.py`](../../tests/core/excel_target/test_excel_target_review_discovery.py) | منع الاسم غير المرتبط، variant conflicts، ambiguous rows، stable ordering، ومنع تطابق الأرقام وحدها. |
| اختبارات artifacts | [`test_excel_target_manual_review_artifacts.py`](../../tests/cli/commands/test_excel_target_manual_review_artifacts.py) | كتابة CSV/JSONL، compatibility metadata، target source، وحالة عدم وجود identity. |
| اختبارات coverage/evaluator | [`test_coverage.py`](../../tests/core/excel_target/test_coverage.py) و[`test_excel_target_evaluator.py`](../../tests/core/excel_target/test_excel_target_evaluator.py) | عدم استدعاء Cohere في تقرير coverage، وصحة gold/safety/data-quality. |
| تحليل approvals | [`test_approved_correction_analysis.py`](../../tests/core/excel_target/test_approved_correction_analysis.py) | replay بدون saved approval، stale/scope/ambiguous، وعدم استدعاء lookup أو rebind في المسار المعطّل. |
| فرضيات قائمة | [`tests/hypotheses`](../../tests/hypotheses) | أغلبها يختبر auto-save وقرار Tawreed العام؛ لا يغطي وحده recall لقائمة Excel-target اليدوية. |

### ملاحظة عن الحالة الحالية للمستودع

وقت الفحص كان working tree يحتوي تغييرات قائمة في ملفات matcher/config/tests،
وقواعد بيانات وملفات Excel غير متتبعة. لذلك لا يجوز تسمية الحالة الحالية
“before” أو “after” قبل حفظ `git commit`/ `git diff` وhashes للمدخلات. لا
تُستخدم هذه الوثيقة لتبرير reset أو checkout أو حذف أي من تلك التغييرات.

## 3. تعريف المرشح: ثلاث مجموعات لا مجموعة واحدة

العبارة “إظهار كل المرشحين” تحتاج تعريفًا قابلًا للقياس. يجب فصل المجموعات التالية
في كل صف manual-review:

| الرمز | التعريف | هل يقيس recall؟ |
|---|---|---|
| `C_universe` | كل صفوف target التي اجتازت predicate الاكتشاف المعلن، قبل أي حد حفظ أو عرض. يجب أن يكون لها row key وscore وسبب inclusion. | نعم؛ هذا هو المقام المرجعي لاكتشاف أن المرشح لم يُكتشف أصلًا. |
| `C_saved` | المرشحون الذين كُتبوا في `manual_review_candidates_*.jsonl` وفي حقول CSV. | نعم، لكن قد يفشل بسبب save cap. |
| `C_display` | المرشحون الذين تعرضهم الواجهة بعد حد العرض/pagination. | يقيس قابلية الاستخدام، لا قدرة matcher وحدها. |

المصدر الحالي يطبق `ReviewDiscoveryConfig.limit` داخل matcher، ثم يطبق
`manual_review_save_candidate_limit` داخل writer. وفي `state/config.yaml` القيم
الحالية هي discovery limit = 5، save limit = 30، display limit = 5، بينما
`config.example.yaml` يضع save limit = 10. لذلك:

- `candidate_count_total` الحالي هو total بعد discovery limit الحالي، وليس عدد
  كل صفوف الكتالوج التي كان يمكن فحصها.
- زيادة save limit وحدها لا تعيد مرشحًا استُبعد قبل writer.
- زيادة display limit وحدها لا تحسن recall في artifact.
- لا يُقبل ادعاء “كل المرشحين” إلا إذا أمكن قياس `C_universe` أو صيغ predicate
  bounded واضحة، ثم حفظ `universe_count` و`candidate_count_saved` منفصلين.

هذا الفصل يجب أن يظهر في test assertions وmanifest، حتى لا يخفي cap مشكلة
VOLTAREN أو ZITHRON.

## 4. خط الأساس gold set

### 4.1 شكل ملف gold المقترح

يُنشأ fixture اختباري immutable خارج `state/`، مثل:

```csv
item_code,item_name,target_key,expected_row_key,expected_store_product_id,label,expected_category
...,VOLTAREN 3AMP,البركة شركات,<sha256-row-key>,<id>,correct,excel_target_candidate_available
...,زيثرون 3قرص س جديد,البركة شركات,<sha256-row-key>,<id>,correct,excel_target_candidate_available
```

المرجع هو `expected_row_key` الناتج من `(target_key, source_file, source_row,
store_product_id, name)`، لا الاسم وحده ولا product id وحده؛ لأن الكتالوج قد
يحتوي نفس الكود لأكثر من variant. طريقة تكوين row key موجودة في
`excel_target_review_candidates.py`.

يجب أن يحتوي gold على:

- **positive rows:** الحالتان المذكورتان، بعد التحقق من workbook snapshot نفسه.
- **near negatives:** نفس العلامة مع قوة مختلفة، شكل مختلف، pack مختلف، volume
  مختلف، وسطر يحمل suffix مثل `س جديد` إذا كان ذا دلالة في target.
- **ambiguous rows:** صفان متساويا القوة أو نفس product id في source rows مختلفة.
- **unrelated rows:** نفس الأرقام أو token عام دون identity مشتركة.
- **no-catalog/out-of-scope rows:** للتمييز بين فشل المطابقة وفشل scope.

لا يكفي وضع `expected_store_product_id` فقط؛ يجب حفظ source file/row أو row key
حتى لا يمر اختبار يختار صفًا آخر من نفس الكود.

### 4.2 توسيع gold تدريجيًا

الحد الأدنى الأولي هو جميع أمثلة manual-review التي أثبتت المراجعة البشرية
صحتها، ومنها المثالان أعلاه. ثم تُسحب عينة stratified من كل فئة في coverage:

1. identity absent.
2. identity variant rejected.
3. candidate available but rejected/unknown compatibility.
4. ambiguous.
5. stale/scope mismatch.

لا تُحسب الحالات التي لا يوجد صفها في workbook snapshot الحالي ضمن recall؛ تُسجل
كـ `approval_outside_current_input` أو `catalog_drift` وتظهر في تقرير الجودة.

## 5. المقاييس والـ acceptance gates

### 5.1 recall للمرشح الصحيح

لصف gold موجب `i)، ولـ `g_i` row key الصحيح:

```text
found_universe_i = 1 إذا كان g_i ∈ C_universe_i وإلا 0
found_saved_i    = 1 إذا كان g_i ∈ C_saved_i وإلا 0
found_top_k_i    = 1 إذا كان g_i ضمن أول k مرشحين مرتبين وإلا 0

Recall_universe = Σ found_universe_i / عدد gold الموجبة داخل نفس catalog fingerprint
Recall_saved    = Σ found_saved_i    / نفس المقام
Recall@k        = Σ found_top_k_i    / نفس المقام
```

يُنشر كل من recall لكل target (`البركة شركات` و`القيصر شركات`) وoverall، مع
الأعداد الخام والمقام. لا يُستبدل ذلك بعدد الحالات التي أصبحت `manual_review`.

الحد الأدنى للقبول في positive gold بعد التغيير:

- لا توجد حالة موجبة معروفة لا تظهر في `C_universe`.
- لا تختفي أي حالة موجبة كانت ظاهرة في `C_saved` قبل التغيير.
- `Recall_saved` و`Recall@5` يُبلّغان منفصلين؛ إذا كان الهدف عرض أكثر من 5 فلا
  يجوز إبقاء اسم metric يوحي بأن `@5` هو “كل المرشحين”.
- كل positive row يُراجع product/form/strength/pack يدويًا مرة واحدة على الأقل
  عند اعتماد gold.

### 5.2 عدم توسيع المرشحين الخطأ بلا حدود

لكل item manual-review، سجّل:

- `|C_universe|`, `|C_saved|`, `|C_display|`.
- المتوسط، الوسيط، p95، p99، وmax لكل target.
- `wrong_candidate_count = |C_saved| - 1` في positive rows، و`|C_saved|` في
  negative rows.
- نسبة الحالات التي لا يوجد فيها أي candidate، ونسبة الحالات التي زاد فيها
  العدد عن baseline بنسبة 2x أو تخطى budget المعلن.
- عينة precision يراجعها إنسان: `relevant_saved / saved`، مع تعريف relevant
  يتضمن identity وvariant compatibility ولا يعتبر matching فقط.

حواجز صلبة:

- `saved_count <= configured_save_limit` لكل صف.
- `display_count <= configured_display_limit` قبل pagination.
- `saved_count <= universe_count` و`manual_review_required` لا يكون true مع
  `universe_count = 0`.
- لا يوجد candidate مصدره Tawreed أو target آخر.
- لا يُرفع threshold إلى درجة تجعل المرشح الصحيح يظهر عبر قائمة ضخمة من rows
  غير مرتبطة؛ الزيادة المقبولة تحتاج سببًا موثقًا في gold وcandidate-size
  histogram.

الهدف ليس تقليل المرشحين إلى واحد دائمًا؛ الهدف قائمة مراجعة bounded تحتوي الصف
الصحيح ولا تُغرق المراجع بصفوف غير مرتبطة. أي تغيير في cap أو threshold يجب أن
يُقارن على نفس gold ونفس catalog fingerprint.

### 5.3 سلامة المطابقة التلقائية

افصل هذه المقاييس عن manual-review recall:

- `automatic_verified`: نتيجة matcher الآلية التي تحمل evidence آمنًا.
- `approved_manual_override`: نتيجة approval بشرية row-scoped.
- `saved_auto_matched`: قرار حفظ آلي سابق، وهو provenance لا مكسب جديد.
- `manual_review`: حالات ما زالت تحتاج إنسانًا.

المكسب الرئيسي:

```text
automatic_gain = automatic_verified_after - automatic_verified_before
```

لا يدخل `approved_manual_override` في هذا الفرق. يجب أن تساوي هذه الحواجز صفرًا:

- auto-match مبني فقط على `review_fuzzy`.
- auto-match مبني فقط على `cohere_translation` تحت `matching-risk-policy=safe`.
- auto-match مع `compatibility_status=rejected` دون approval صريح.
- auto-match من source غير Excel target عند تقييم Excel target.
- positive gold يختار product/row مختلفًا عن المتوقع.

المصدر الحالي يختبر جزءًا من ذلك في `evaluate_excel_target.py` عبر
`_safety_errors`، لكن التقرير المقترح يجب أن يضيف `match_origin` صريحًا بدل
استنتاجه من نص `final_reason`.

### 5.4 determinism

أعد نفس replay مرتين على نفس:

- commit وworking-tree patch.
- config bytes وcatalog/order/prevented workbooks.
- translation-cache snapshot وprovider mode.
- manual-review DB snapshot، أو DB فارغة عند اختبار approval-disabled.
- Python/dependency versions.

قارن بعد إزالة الحقول الزمنية/المسارات المتغيرة فقط:

- item key وtarget key والحالة والproduct/row key.
- قائمة المرشحين وترتيبها وscore وstatus وreason.
- CSV header وrow count وJSONL records canonicalized.
- counts وgold/safety/data-quality errors.

لا تُقارن `match_elapsed_ms` byte-for-byte؛ تُقارن في performance report. أما
semantic output فيجب أن يكون متطابقًا. كذلك شغّل نفس الحالة بـ
`--item-workers 1` و`--item-workers 4` عند توفر بيئة آمنة، ويجب ألا يتغير
اختيار المرشح أو ترتيبه أو counts.

### 5.5 الأداء

لكل target ولكل حجم replay سجّل:

- `catalog_size` و`item_count`.
- index build wall time.
- total match time وaverage per item.
- p50/p95/p99 لـ `match_elapsed_ms` من trace/summary.
- candidate discovery time إن أمكن، وpeak RSS إذا توفر profiler.
- عدد timeout/stop/interrupted items.

مستويات replay:

1. **Smoke:** نفس أمر المستخدم مع `--limit 100`.
2. **Full input:** نفس workbook مع العدد الكامل المتوقع 2397 أو `--limit 0` بعد
   تثبيت عدد items الفعلي والمتبقي بعد prevented-items filter.
3. **Target-only focused:** fixture صغير يحوي VOLTAREN وZITHRON وجميع negatives.

حاجز مبدئي قابل للمراجعة: لا يتجاوز after p95 أو total أكثر من 1.25x baseline
دون sign-off، ولا يتجاوز حد التشغيل الموجود في writer (300 ثانية). إذا تغير
حجم المرشحين عمدًا، يُنشر أثره على الزمن والذاكرة بدل إخفائه داخل متوسط واحد.

## 6. اختبار سلامة artifacts وقواعد البيانات

### 6.1 manifest قبل التشغيل

أنشئ لكل replay manifest غير قابل للتعديل يحوي:

```text
git_sha
working_tree_patch_sha256
python_version
dependency_lock_sha256
config_sha256
order_workbook_sha256
baraka_workbook_sha256
kaisr_workbook_sha256
prevented_workbook_sha256
manual_review_db_sha256
order_runs_db_sha256
translation_cache_snapshot_sha256
target_catalog_fingerprint
item_count_before_filter
item_count_after_filter
command_line
run_id
```

يجب أن يكون `target_catalog_fingerprint` مبنيًا من rows canonicalized، لا من
mtime فقط. أي اختلاف في fingerprint يجعل المقارنة غير صالحة ويحوّل النتيجة إلى
`catalog_drift`.

### 6.2 عزل state

أمر المستخدم هو `--match-only`، لكنه ليس read-only بالكامل: مسار Excel target
قد يحفظ verified matches في `state/manual_review_decisions.db`، وrun persistence
قد يكتب `order_runs.db`. لذلك:

- لا تُشغّل before/after على state production مباشرة.
- استخدم disposable clone/worktree فيه نسخ من قواعد البيانات والـ workbooks، أو
  patch-injected temporary stores داخل test harness.
- استخدم `enable_auto_save_verified_match: false` فقط في counterfactual الذي
  يقيس matcher دون side effects؛ لا تستخدمه كبديل عن exact production replay.
- احفظ hash قبل وبعد لكل DB. في offline analyzer يجب أن يكون hash بعد التشغيل
  مطابقًا لما قبل التشغيل، وأن تُثبت الاختبارات أن `upsert` وrebind لم يحدثا.

### 6.3 invariants للملفات

لكل target/run:

- summary CSV موجود، header واحد، وكل item input يظهر مرة واحدة أو يُفسر سبب
  توقفه.
- `candidate_count_total >= candidate_count >= 0`.
- كل JSONL payload له نفس item key الموجود في CSV.
- كل option target key/source file/row key يطابق workbook الذي تم hash له.
- كل option قابل للطلب يملك `store_product_id` صالحًا، ولا يتحول blank price إلى
  zero تلقائيًا.
- ملفات UTF-8/UTF-8-SIG تُقرأ مجددًا دون فقد النص العربي.
- عند stop/timeout لا يوجد summary نهائي zero-byte أو summary مقبول ناقص بلا
  marker يوضح partial run؛ ملفات temp لا تُعتبر نتيجة.
- إعادة التشغيل لا تستبدل artifact سابقًا بصمت؛ استخدم run id أو directory
  منفصلًا واحفظ manifest.

## 7. خطة before/after قابلة لإعادة التشغيل

### المرحلة A: preflight

1. ثبّت commit وpatch وhashes في manifest.
2. تأكد أن stop flag غير موجود في sandbox؛ إذا كان موجودًا لا تحذفه من production.
3. سجّل عدد صفوف order قبل وبعد prevented-items filter.
4. تحقق أن VOLTAREN وZITHRON ضمن replay؛ قد لا يصل `--limit 100` إليهما.
5. سجّل source file وsource row وrow key لكل gold positive.
6. خذ snapshot read-only من manual-review DB.

### المرحلة B: offline baseline

استخدم `scripts/baraka_coverage_report.py` لكل target، ثم
`scripts/baraka_index_benchmark.py`، في directory منفصل. هذا المسار لا يرسل
طلبًا ولا يغيّر cart، لكنه يقيس matcher والـ coverage فقط.

### المرحلة C: exact operational replay

شغّل نفس أمر المستخدم في disposable clone مع artifact root وrun id معزولين.
صحح رابط `run.py` إلى path فعلي ولا تغيّر flags المقاسة. هذا التشغيل لا يضيف
إلى cart بسبب `--match-only`، لكنه قد يكتب artifacts وقواعد SQLite، لذلك يمنع
تشغيله على state الإنتاجية.

### المرحلة D: المقارنة

قارِن CSV قبل/بعد بواسطة:

`python scripts/evaluate_excel_target.py --before <before.csv> --after <after.csv> --gold <gold.csv> --output <comparison.json>`

افشل المقارنة عند gold failure أو safety/data-quality error أو matched-set change
غير مفسر أو candidate tail فوق budget أو semantic output غير deterministic.

## 8. الاختبارات المقترحة وأوامر التشغيل

المجموعة الحالية التي يجب أن تمر قبل وبعد:

`python -m pytest tests/core/excel_target/test_excel_target_review_discovery.py tests/core/excel_target/test_excel_target_review_candidates.py tests/core/excel_target/test_product_attributes.py tests/core/excel_target/test_excel_target_aliases.py tests/core/excel_target/test_baraka_safe_matching.py tests/core/excel_target/test_coverage.py tests/core/excel_target/test_approved_correction_analysis.py tests/cli/commands/test_excel_target_manual_review_artifacts.py tests/cli/commands/test_excel_target_e2e.py tests/core/config/test_matching_config.py -q`

ثم:

`python -m pytest tests/hypotheses -q`

و:

`python tests/hypotheses/automatched/run_all.py`

هذه أسماء اختبارات جديدة مقترحة، وليست ادعاءً بأنها أُضيفت أو نُفذت:

| test name | العقد | الخطر |
|---|---|---|
| `test_voltaren_3amp_gold_row_is_in_universe_and_saved_candidates` | row key الصحيح لفولتارين يظهر في universe وsaved. | استمرار فقدان المرشح خلف cap/normalization. |
| `test_zithron_three_tablets_gold_row_is_in_universe_and_saved_candidates` | نفس العقد لزيثرون 3قرص س جديد. | إصلاح حالة واحدة فقط. |
| `test_gold_candidate_recall_is_measured_by_row_key_not_name` | لا يكفي الاسم أو code لاختيار row. | اختيار variant خاطئ من نفس الكود. |
| `test_candidate_universe_count_is_distinct_from_saved_count` | total قبل save cap منفصل عن saved. | recall وهمي بسبب field قديم. |
| `test_candidate_count_stays_within_configured_budget` | كل item يحترم discovery/save/display budgets. | candidate explosion وOOM. |
| `test_variant_conflicts_remain_review_candidates_but_never_auto_match` | اختلاف strength/form/pack يبقى review-only. | false auto-match. |
| `test_unrelated_numeric_overlap_does_not_create_candidate` | الأرقام المشتركة وحدها لا تكفي. | مرشحون غير مرتبطين. |
| `test_target_candidate_provenance_never_leaks_tawreed_rows` | كل option من catalog target المحدد. | source leakage. |
| `test_equal_score_candidates_have_stable_row_key_order` | tie/ambiguous order ثابت. | nondeterminism. |
| `test_repeated_replay_has_identical_semantic_artifacts` | CSV/JSONL/counts متطابقة مع تجاهل timing. | diff غير موثوق. |
| `test_workers_one_and_four_have_same_candidate_semantics` | worker count لا يغير القرار أو القائمة. | race/order dependency. |
| `test_counterfactual_disables_saved_lookup_and_rebind` | لا lookup/upsert/rebind في counterfactual. | تضخيم metric بالـ approvals. |
| `test_existing_approved_row_scope_and_stale_row_guards_unchanged` | valid row يعمل وstale/wrong target لا يفرض match. | كسر backward compatibility. |
| `test_summary_and_jsonl_have_matching_item_keys_and_counts` | CSV وJSONL متوافقان بلا duplicate keys. | artifact corruption. |
| `test_stop_or_timeout_never_publishes_zero_byte_final_summary` | partial run لا يبدو نجاحًا. | baseline ناقص. |
| `test_before_after_harness_leaves_state_db_hash_unchanged` | offline replay لا يغير DB. | تلوث القياس. |

### اختبارات mutation/property

غيّر property واحدة في target row كل مرة: strength، form، pack، source row،
duplicate code، ترتيب rows، صف unrelated بنفس الرقم، وduplicate physical row.
المتوقع أن يتغير row key عند تغير identity material، ويبقى candidate ordering
ثابتًا، ولا يتحول variant conflict إلى auto-match، ولا تتضخم duplicates بلا حد.

## 9. backward compatibility checklist

يُقارن before/after على نفس item key، وليس على totals فقط:

- matched set للصفوف التي كانت matched يبقى نفسه product id/row source.
- no-results التي لم تكن gold positive لا تتحول تلقائيًا لمطابقة بسبب fuzzy
  candidate فقط.
- saved `approved_match` لا يتحول إلى global alias؛ يبقى exact target-row
  override فقط.
- stale approval وwrong target لا يمنعان discovery الحالي ولا يفرضان candidate.
- `--match-only` يبقى بلا cart gate/mutation، مع بقاء CSV/JSONL/Run DB semantics.
- headers القديمة لا تُحذف؛ الحقول الجديدة تُضاف backward-compatible ويستطيع
  evaluator قراءة old artifacts.
- `store_candidates: false` لا يغير manual-review candidate artifacts المقصودة
  ولا يسبب تسريبًا غير متوقع إلى order-runs DB.
- disabled discovery (`excel_target_review_candidates_enabled=false`) يعيد
  no-review-candidates كما قبل، مع بقاء automatic matching safety مستقلة.
- missing/empty target وblank price وzero price تبقى الحالات الموثقة في اختبارات
  loader/e2e، ولا تتحول blank إلى zero.

## 10. المخاطر والتخفيف

| الخطر | أثره | الإشارة/التخفيف |
|---|---|---|
| `--limit 100` لا يحتوي VOLTAREN/ZITHRON | recall يبدو صفرًا رغم أن النظام لم يرَ الصفين | preflight يثبت item membership، ثم focused replay/full replay. |
| catalog workbook تغيّر بين قبل وبعد | row key وrecall غير قابلين للمقارنة | fingerprint/hash، وإبطال المقارنة عند drift. |
| `manual_review_save_candidate_limit` أكبر من discovery limit | تغيير save limit لا يصلح فقدان candidate | report universe/saved منفصل، واختبار limits matrix. |
| live Cohere/cache غير مثبت | اختلاف identity أو candidate set بين التشغيلين | cache snapshot/provider status أو وسم النتيجة non-comparable. |
| saved approvals تدخل في after فقط | تضخيم automatic gain | approval-disabled counterfactual و`match_origin` منفصل. |
| fuzzy threshold منخفض جدًا | candidate explosion وfalse positives | p95/p99/max، negative gold، وbudget gate. |
| fuzzy threshold مرتفع جدًا | recall يفشل، خاصة typo/Arabic spelling | positive gold لكل حالة معروفة وRecall_universe. |
| source leakage بين Tawreed/target | مرشح يبدو صحيحًا لكنه ليس من workbook المقصود | provenance assertion وtarget-only catalog fixture. |
| nondeterministic tie-break | diff متغير وقرارات مختلفة | canonical row key ordering وrepeat/workers test. |
| artifact partial overwrite | loss of audit evidence | temp/final invariant، run id منفصل، stop/timeout test. |
| DB writes أثناء القياس | baseline ملوث ونتائج غير قابلة للتكرار | sandbox DB hashes، patch store، `use_saved_approvals=False`. |
| تغير config أو dirty worktree | لا نعرف ما الذي سبب التحسن | manifest للـ SHA/patch/config، وعدم اعتبار working tree الحالي baseline. |
| manual labels غير مستقلة | precision/recall متفائلة | reviewer ثانٍ أو adjudication، وتثبيت label provenance. |

## 11. نموذج تقرير النتيجة

يجب أن يحتوي التقرير النهائي، لكل target ثم aggregate، على الأقل:

~~~text
run_id / git_sha / config_sha256 / catalog_fingerprint
input_count_before_filter / input_count_after_filter
gold_positive_count / gold_out_of_scope_count
recall_universe / recall_saved / recall_at_1 / recall_at_5
candidate_count_total: mean/p50/p95/p99/max
candidate_count_saved: mean/p50/p95/p99/max
wrong_candidate_count و manual-review workload
automatic_verified_before / automatic_verified_after / automatic_gain
approved_manual_override_before / after (informational only)
matched_set_changed_count
safety_errors / data_quality_errors / gold_failures
index_build_ms / match_total_ms / match_p50_ms / match_p95_ms / timeout_count
semantic_determinism_hash_equal
manual_review_db_hash_equal / order_runs_db_hash_equal
artifact_paths و artifact_sha256
~~~

قرار النشر يكون واحدًا من:

- **PASS:** recall gold لا ينخفض، الحالات المطلوبة مسترجعة، لا safety/data
  errors، candidate tail داخل budget، determinism سليم، ولا state mutation.
- **CONDITIONAL:** recall تحسن لكن candidate tail/performance أو labels تحتاج
  review؛ لا يفعّل automatic matching.
- **FAIL:** أي false auto-match، مصدر خاطئ، اختلاف غير مفسر، artifact corruption،
  DB mutation في مسار يفترض أنه read-only، أو gold failure.

## 12. حدود هذه الوثيقة

لم تُنفذ إصلاحات، ولم تُغيّر thresholds أو flags أو production code أثناء إعداد
هذه الاستراتيجية. كما لم يُعتبر أي تشغيل جديد before/after تلقائيًا صالحًا؛ صلاحية
النتيجة مشروطة بالـ sandbox والmanifest وgold/catalog fingerprints المذكورة أعلاه.
