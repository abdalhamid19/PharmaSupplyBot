# خريطة استدعاء مرشحي المراجعة اليدوية في Excel target

## نطاق التحقيق

هذا المستند هو خريطة كود وتحقيق read-only لمسار Excel target من قراءة صفوف
الـ workbook إلى بناء identity، ثم scoring/compatibility، ثم إنشاء مرشحي
المراجعة وكتابة CSV/JSONL. لا يحتوي التحقيق على إصلاح، ولم يُعدّل كود الإنتاج
أو الاختبارات الموجودة. الملف الوحيد المقصود إنشاؤه هو هذا التقرير.

المصادر الأساسية هنا هي الكود الحالي، الاختبارات الحالية، وملفات artifacts
المحلية. حالة المستودع قبل كتابة التقرير كانت dirty؛ توجد تغييرات مستخدم
مسبقة في `src/core/excel_target/*` و`tests/core/excel_target/*` وملفات state
والـ input. لذلك يجب قراءة أرقام السطور أدناه باعتبارها أرقام نسخة working
tree الحالية، لا كاقتراح لإعادة كتابة تلك التغييرات.

## النتيجة المختصرة

فقد المرشح الصحيح في حالتي:

- `VOLTAREN 3AMP` ← الصف العربي الصحيح `فولتارين 3مبول س جديد`.
- `XITHRONE 500MG 3TAB` ← الصف العربي الصحيح `زيثرون 3قرص س جديد`.

يمكن تتبع الفقد إلى مرحلتين قبل artifact writer:

1. فهرس identity يربط aliases الإنجليزية بصفوف الكتالوج عبر مساواة مفتاح
   عربي مطبّع exact. التطبيع الحالي لا ينتج نفس المفتاح للصفين الصحيحين
   ولـ alias dictionary/Tawreed: ينتج مثلًا `فولتارين 3مبول س` و`زيثرون س`
   للصفين الصحيحين، بينما alias identity هو `فولتارين`/`زيثرون`. لذلك لا
   يدخل الصف الصحيح في `by_tawreed_brand` أو `by_dictionary_brand`.
2. طبقة review discovery تختار projection واحدة حسب لغة طلب الصنف. الطلبان
   إنجليزيان، وكتالوج البركة لهذه الصفوف عربي فقط؛ لذلك تستخدم `_english_entries`
   التي لا تحتوي هذه الصفوف، ولا يوجد fallback عربي-إنجليزي fuzzy مستقل يعثر
   عليهما.

بعد ذلك، writer يكتب بأمان ما وصله فقط. الدليل أن artifact البركة في
`20260909_1457` يعلن `candidate_count_total=1` ويحفظ مرشحًا واحدًا خاطئًا،
وليس قائمة تحتوي الصف الصحيح ثم تحذفه أثناء CSV/JSONL serialization.

يوجد أيضًا gap مستقل في parsing للرموز الملتصقة مثل `3AMP` و`3مبول`. هذا لا
يفسر وحده غياب المرشح من القائمة، لكنه يحدد ما ينبغي أن تكون عليه نتيجة
compatibility بعد إعادة إدخاله: مرشح مراجعة مرفوض/غير مثبت مع سبب واضح، لا
match تلقائيًا بلا دليل.

## دليل الحالة الواقعية

### الصفوف موجودة في workbook

قراءة `data/input/excel target/محروس1.xlsx` بـ `openpyxl` أظهرت:

| source row | raw name |
|---:|---|
| 2344 | `زيثرون  500-- 5قرص` |
| 2345 | `زيثرون 3قرص س جديد` |
| 3100 | `فولتارين 3مبول س جديد` |
| 3101 | `فولتارين 50مجم - 20قرص` |
| 3102 | `فولتارين 6امبولة شركه` |

إعداد البركة لا يطلب code column، ولذلك الصفوف code-less ليست مرفوضة من
التحميل: `state/config.yaml:99-106` يحدد `name_col`, `price_col`, و
`discount_col` فقط. في loader، الصف الفارغ الاسم فقط يُسقط في
`_row_to_product`، أما code الفارغ فيُسمح به عندما `requires_code` false
([`excel_target_loader.py:262-302`](../../src/core/excel_target/excel_target_loader.py:262)).

كل صف يحصل على identity مستقر حتى بدون code: `store_product_id` يستخدم code
إن وجد، وإلا SHA-256 من source file وsource row والاسم المطبّع
([`excel_target_loader.py:41-85`](../../src/core/excel_target/excel_target_loader.py:41)).
إذن الدليل الحالي لا يشير إلى أن الصف 3100 أو 2345 ضاع بسبب غياب code أو
تصادم `store_product_id`.

مسار اختيار الملفات وتحميلها هو:

- `selected_excel_target_configs`: أولوية `--excel-target` ثم overrides
  والـ default path، مع الحفاظ على ترتيب targets
  ([`cli_order_excel_target.py:38-98`](../../src/cli/commands/cli_order_excel_target.py:38)).
- `load_target_catalogs`: يقرأ كل file ويجمع الصفوف، ويمرر اسم الملف كـ
  `source_file` لكل `TargetProduct`
  ([`cli_order_excel_target.py:101-132`](../../src/cli/commands/cli_order_excel_target.py:101)).
- loader يختار sheet/header والـ columns ثم يبني قائمة المنتجات
  ([`excel_target_loader.py:143-185`](../../src/core/excel_target/excel_target_loader.py:143)).

### ما سجله run `wardany/20260909_1457`

في:

`artifacts/excel-target/البركة شركات/20260909_1457/`

سجل `match_only_summary_البركة شركات.csv` وملف
`manual_review_excel-target_البركة شركات.csv` ما يلي:

| item | candidate_count_total | source | reported rejection |
|---|---:|---|---|
| `VOLTAREN 3AMP` (`vol3`) | 1 | `محروس1.xlsx` | `candidate has an unrequested strength` |
| `XITHRONE 500MG 3TAB` (`73852`) | 1 | `محروس1.xlsx` | `candidate strength is not proven` |

لكن `manual_review_candidates_excel-target_البركة شركات.jsonl` يحفظ:

- لـ `VOLTAREN 3AMP`: الصف 3101، `فولتارين 50مجم - 20قرص`.
- لـ `XITHRONE 500MG 3TAB`: الصف 2344، `زيثرون  500-- 5قرص`.

ولا يحفظ الصف 3100 أو 2345. هذه المقارنة تفصل موضع العطل: لو كان writer
يحذف المرشح الصحيح، لكان `candidate_count_total` أو payload يتضمنه قبل
الكتابة. الموجود هو أن upstream سلّم مرشحًا واحدًا فقط.

## خريطة المسار التنفيذي

### 1. إنشاء matcher وفهرسة الكتالوج

`ExcelTargetMatcher.__init__` يحفظ catalog كما حمّله، ويبني:

- `ExcelTargetBilingualIndex` للهوية.
- `ExcelTargetReviewDiscoveryIndex` للاكتشاف review-only.
- `catalog_by_id` لربط diagnostics بصفوف target الفعلية.
- `native_english_candidate_templates` فقط للصفوف التي لديها
  `trusted_name_en`.

المواضع: [`excel_target_matching.py:59-87`](../../src/core/excel_target/excel_target_matching.py:59).

في البركة، `TargetProduct.trusted_name_en` يعود فارغًا للاسم العربي أو
المختلط ([`excel_target_loader.py:63-69`](../../src/core/excel_target/excel_target_loader.py:63)).
لذلك لا يكون native English scoring هو مصدر هوية الصفوف العربية؛ يعتمد
المسار أساسًا على bilingual identity أو discovery.

### 2. قرار المطابقة وترتيب الاستدعاء

`ExcelTargetMatcher.match` ينفذ بالترتيب التالي:

1. saved approval scoped قد ينهي المسار مبكرًا في السطور 94-97.
2. `identity_index.identify(item.name)`.
3. `_compatible_identified` يفصل `accepted` عن `rejected`.
4. صف compatible وحيد يصبح match؛ أكثر من صف يصبح ambiguous.
5. إذا لم يوجد accepted، يحاول `_native_english_decision` فقط على templates
   الإنجليزية، ثم يضع سبب الرفض/غياب الهوية.
6. بعد ذلك فقط يشغل review discovery ويبني `review_candidates`.

المواضع: [`excel_target_matching.py:89-129`](../../src/core/excel_target/excel_target_matching.py:89).

هذا مهم للحالة: `review_candidates` ليست view على كل catalog. هي ناتج
مجموعات evidence محددة بعد أن يكون identity وdiscovery قد أعادا صفوفًا.

### 3. Identity normalization والـ alias join

عند بناء `ExcelTargetBilingualIndex`:

- الصفوف العربية تُجمع في `by_arabic_brand` بمفتاح
  `normalize_arabic_brand(product.name_ar)`، السطور 101-107.
- `target_by_arabic` يعيد التجميع بالمفتاح نفسه، السطور 108-116.
- كل Tawreed row يُطبّع English وArabic، ثم لا يربط بالكتالوج إلا إذا وجد
  `targets = target_by_arabic.get(arabic_brand, ())`، السطور 117-131.
- dictionary rows تمر بنفس شرط exact key في السطور 133-148.
- `identify` يبحث عن English brand exact في `by_tawreed_brand` و
  `by_dictionary_brand`، ثم cached translations وaliases، السطور 199-248.

المصدر: [`excel_target_identity.py:94-248`](../../src/core/excel_target/excel_target_identity.py:94).

النتيجة المقاسة من working tree الحالي:

```text
normalize_arabic_brand("فولتارين 3مبول س جديد") -> "فولتارين 3مبول س"
normalize_arabic_brand("فولتارين 50مجم - 20قرص") -> "فولتارين"
normalize_arabic_brand("زيثرون 3قرص س جديد")       -> "زيثرون س"
normalize_arabic_brand("زيثرون  500-- 5قرص")       -> "زيثرون"
```

وهذا يطابق artifact: alias `VOLTAREN` يربط الصف الذي مفتاحه `فولتارين`،
وalias `XITHRONE` يربط الصف الذي مفتاحه `زيثرون`، بينما الصفان الصحيحان
بقيَا خارج mapping.

الـ alias resolver لا يمثل fallback شاملًا لهذه الحالة. عند إنشائه، لا يفهرس
إلا alias entries التي يطابق جانبها العربي صفًا موجودًا في
`targets_by_arabic`، ثم يعيد products لذلك المفتاح فقط
([`excel_target_aliases.py:187-245`](../../src/core/excel_target/excel_target_aliases.py:187)).
لذلك إذا كان normalization key للصف الصحيح مختلفًا، فلن تنقذه threshold أو
approved alias؛ الفقد يسبق resolver.

### 4. Review discovery وسبب عدم الإنقاذ

`ExcelTargetReviewDiscoveryIndex.build` يبني projection منفصلة:

- `_english_entries` من `product.trusted_name_en` فقط، السطور 114-125.
- `_arabic_entries` من `product.name_ar` إذا احتوى Arabic، السطور 127-137.

المواضع: [`excel_target_review_discovery.py:89-143`](../../src/core/excel_target/excel_target_review_discovery.py:89).

عند discovery، `_query_projection` يختار projection واحدة فقط:

- إذا الطلب يحتوي Arabic: `arabic_fuzzy`.
- وإلا: `english_fuzzy`.

ولا يجمع projectionين ولا يستخدم ترجمة داخلية لهذا الاستدعاء
([`excel_target_review_discovery.py:145-196`](../../src/core/excel_target/excel_target_review_discovery.py:145)).

لذلك:

```text
item = "VOLTAREN 3AMP"          -> english_fuzzy
item = "XITHRONE 500MG 3TAB"    -> english_fuzzy
Baraka rows above               -> Arabic-only, no trusted_name_en
```

والفحص المباشر الحالي أعاد `discovery_hits=()` للحالتين. هذا ليس bug في
الـ writer؛ إنه contract مقصود في discovery لمنع مقارنة Arabic كأنه English.
لكن contract الحالي يترك فجوة recall عندما يكون الطلب English والكتالوج
Arabic-only ولا توجد هوية exact.

حتى داخل projection الصحيحة، discovery ليس exhaustive: `_score_entries` لا
يحتفظ إلا بصف لديه shared meaningful token وscore أعلى من minimum، ثم
`_select_scored_candidates` يمرر ambiguous أو strong أو medium فقط
([`excel_target_review_discovery.py:199-239`](../../src/core/excel_target/excel_target_review_discovery.py:199)).
ويقطع الناتج إلى `config.limit` في السطور 172-184. هذه نقطة مستقلة يجب ألا
تختلط مع فقد الصفين الحاليين قبل scoring.

اختبارات discovery الحالية تثبت السلوك intended لمدخلات من نفس projection:

- English typo مع English catalog في
  [`test_excel_target_review_discovery.py:15-39`](../../tests/core/excel_target/test_excel_target_review_discovery.py:15).
- Arabic spelling noise مع Arabic catalog في
  [`test_excel_target_review_discovery.py:106-128`](../../tests/core/excel_target/test_excel_target_review_discovery.py:106).
- variant conflicts تُحفظ للمراجع في
  [`test_excel_target_review_discovery.py:131-159`](../../tests/core/excel_target/test_excel_target_review_discovery.py:131).

لا يوجد اختبار يثبت أن English order item مع Arabic-only target catalog يجب
أن يجد صفًا عربيًا مكافئًا، ولا اختبار خاص بالصياغتين `3مبول س جديد` و`3قرص
س جديد`.

### 5. Scoring وdiagnostics

هناك مساران scoring مختلفان يجب عدم دمجهما في التشخيص:

#### Native English target rows

إذا كانت catalog rows إنجليزية، يستخدم `_native_english_decision`:

- يولد queries من الاسم الكامل، normalized name، prefixes، وtoken windows
  عبر [`product_matching_queries.py:8-41`](../../src/core/matching/product_matching_queries.py:8).
- يمرر candidate templates إلى `explain_best_product_match` في
  [`excel_target_matching.py:423-441`](../../src/core/excel_target/excel_target_matching.py:423).
- scoring يحسب sequence/overlap/numeric/exact/availability والـ lexical
  penalties، ثم sort key ثابتًا في
  [`product_matching_scoring.py:173-220`](../../src/core/matching/product_matching_scoring.py:173)
  و[`product_matching_scoring.py:271-299`](../../src/core/matching/product_matching_scoring.py:271).
- acceptance يمر عبر exact/high-overlap/medium/numeric checks في
  [`matching_rules.py:71-150`](../../src/core/matching/matching_rules.py:71).
- diagnostics تُبنى لكل result بعد deduplication، ثم top-k optimization
  يطبق component checks ويضع سبب `Skipped by candidate top-k optimization`
  بدل إسقاط diagnostic بالكامل
  ([`product_matching_decisions.py:68-109`](../../src/core/matching/product_matching_decisions.py:68)).

#### Arabic-only target rows

في حالة البركة الحالية، لا يوجد English template، ولذلك لا توجد نتيجة
scoring native قادرة على إعادة الصف 3100/2345. المرشح الذي ظهر في artifact
جاء من identity alias (`tawreed_catalog`) ثم خضع للـ compatibility، وليس من
English fuzzy discovery.

### 6. Compatibility: ما الذي يحدث بعد وصول الصف

`_compatible_identified` يتجاهل Cohere identity للـ automatic acceptance، ثم
يشغل `validate_product_compatibility` على كل identified product
([`excel_target_matching.py:187-201`](../../src/core/excel_target/excel_target_matching.py:187)).

الـ compatibility parser يستخرج forms/strengths/packs/concentrations في
[`product_attributes.py:95-129`](../../src/core/excel_target/product_attributes.py:95).
أسباب الرفض مرتبة في `_mismatch_reason`:

- form غير مثبت أو متعارض، السطور 235-240؛
- concentration، السطور 240-247؛
- strength، السطور 248-259؛
- candidate strength غير مطلوب، السطور 260-261؛
- pack غير مثبت أو متعارض، السطور 262-265.

المرشح المرفوض لا ينبغي أن يختفي من manual review: discovery يحسب
compatibility ثم يبني `ReviewDiscoveryHit` مع status وattribute note
([`excel_target_review_discovery.py:242-260`](../../src/core/excel_target/excel_target_review_discovery.py:242)).
كما أن `ExcelTargetReviewCandidate.review_status` يميز `variant_unproven`
و`variant_conflict` ([`excel_target_review_candidates.py:92-109`](../../src/core/excel_target/excel_target_review_candidates.py:92)).

لكن توجد فرضية parsing يجب اختبارها منفصلة:

- `_has_alias` يستخدم `\b` للـ ASCII aliases في
  [`product_attributes.py:158-162`](../../src/core/excel_target/product_attributes.py:158)،
  ولذلك `AMP` الملتصقة بالرقم في `3AMP` لا تُعامل بالضرورة مثل `3 AMP`.
- جدول AMPOULE الحالي يحتوي صيغ `امبول`/`امبولة` في
  [`product_attributes.py:20-28`](../../src/core/excel_target/product_attributes.py:20)،
  ولا يثبت تلقائيًا الصيغة المختصرة `مبول` الموجودة في الصف 3100.
- القياس الحالي أعطى للصف 3100 `candidate pack is not proven`، ولصف 2345
  في طلب `XITHRONE 500MG 3TAB` `candidate strength is not proven`.

هذه نتيجة compatibility بعد محاولة فحص الصف يدويًا، وليست سبب غيابه من
artifact. إذا أُعيد الصف إلى candidate set، فالسياسة الصحيحة للمراجعة هي
إظهاره مع evidence/rejection، مع إبقاء automatic acceptance مغلقًا إلى أن
تثبت كل attributes.

### 7. بناء قائمة المرشحين

`build_review_candidates` يقبل ثلاثة sources فقط:

1. `discovery_hits`؛
2. `identified`؛
3. `diagnostics` التي يكون `storeProductId` الخاص بها قابلًا للربط بصف في
   catalog الحالي.

المواضع: [`excel_target_review_candidates.py:165-257`](../../src/core/excel_target/excel_target_review_candidates.py:165).

كل candidate يحتفظ بصف target الحقيقي، score، compatibility، identity
evidence، method، margin، shared tokens، source file، وstable row key
([`excel_target_review_candidates.py:27-162`](../../src/core/excel_target/excel_target_review_candidates.py:27)).

بعد الجمع:

- `_keep_best` يدمج نفس row key ويحتفظ بأعلى score فقط
  ([`excel_target_review_candidates.py:301-308`](../../src/core/excel_target/excel_target_review_candidates.py:301)).
- القائمة ترتب بالscore/evidence/code/name.
- `limit` إن وجد يقطع القائمة في السطور 259-273.

هذا يعني أن عبارة "كل المرشحين" تحتاج تعريفًا دقيقًا: الكود الحالي يعرض كل
المرشحين الذين نجحوا في evidence gates، وليس كل صفوف catalog التي تحمل brand
متشابهًا. كما أن المرشح الصحيح الحالي لا يصل إلى `_keep_best` أصلًا.

### 8. الكتابة إلى CSV وJSONL

في CLI، artifact paths تُفتح داخل `run_excel_target_match_only`:

- summary CSV؛
- summary JSONL؛
- manual-review CSV؛
- target-specific manual-review candidates JSONL.

المواضع: [`cli_order_excel_target.py:162-224`](../../src/cli/commands/cli_order_excel_target.py:162).

عندما لا يوجد best match، الكود يأخذ `result.review_candidates`، يحدد
`candidate_count_total` قبل الحفظ، ثم يقطع المرشحين إلى `review_limit`
([`cli_order_excel_target.py:278-346`](../../src/cli/commands/cli_order_excel_target.py:278)).
بعد ذلك يكتب summary CSV وsummary JSONL مع counts/evidence/reason، لكنه لا
يضع أسماء كل options داخل summary JSONL
([`cli_order_excel_target.py:348-395`](../../src/cli/commands/cli_order_excel_target.py:348-395)).

الـ detailed candidates تُكتب في `_append_excel_target_review_artifacts`:

- CSV يجمع counts والـ provenance والـ compatibility؛
- JSONL يضع `options`، وكل option يحمل target/source/row key وmethod وscore
  وcompatibility.

المواضع: [`cli_order_excel_target.py:587-682`](../../src/cli/commands/cli_order_excel_target.py:587).

يوجد حدّان مختلفان ينبغي تتبعهما في أي اختبار:

- `excel_target_review_candidate_limit: 5` هو حد discovery نفسه من
  [`cli_order_excel_target.py:461-484`](../../src/cli/commands/cli_order_excel_target.py:461)
  وconfig `state/config.yaml:71-78`.
- `manual_review_save_candidate_limit: 30` يحدد الحفظ في CLI عبر
  [`cli_order_excel_target.py:555-565`](../../src/cli/commands/cli_order_excel_target.py:555)،
  لكنه لا يعيد مرشحين فقدوا قبل ذلك.

إذن رفع حد الحفظ من 30 لا يصلح فقد الصف 3100/2345 ولا يجعل القائمة
exhaustive إذا كان discovery limit ما زال 5.

`scripts/baraka_coverage_report.py` يوفر مسار تقرير read-only منفصلًا، ويبني
الصف من `matcher.match` مرة واحدة ثم يضيف candidate counts/methods/scores/row
keys في السطور 63-136، ويكتب CSV وJSONL في السطور 239-263
([`baraka_coverage_report.py:63-136`](../../scripts/baraka_coverage_report.py:63)).
لكنه يعيد استخدام نفس `matcher.review_candidates`؛ لذلك لا يمكنه استعادة صف
لم يخرجه identity/discovery.

## الفرضيات المرتبة

### H1 — السبب الأرجح: exact Arabic-key mismatch

**الدليل:** الصفان الصحيحان موجودان في workbook، لكن مفاتيحهما الحالية لا
تساوي مفاتيح alias (`فولتارين 3مبول س`/`زيثرون س` مقابل `فولتارين`/`زيثرون`).
identity builder لا يربط إلا `target_by_arabic.get(arabic_brand)` exact.

**الأثر:** الصف الصحيح لا يدخل `identified`، ولا يمكن أن يصل إلى candidate
builder عبر identity أو alias resolver.

**ما يجب اختباره:** جميع spellings الخاصة بــ `س جديد`، و`مبول` مقابل
`امبول`، و`3قرص`/`3 اقراص`، مع negative cases تمنع إسقاط كلمة عربية جزء من
brand فعليًا.

### H2 — فجوة cross-script في review discovery

**الدليل:** English query يختار `english_fuzzy` فقط، وBaraka rows العربية
لا تملك `trusted_name_en`. القياس المباشر أعاد discovery hits فارغة حتى مع
وجود الصفين الصحيحين.

**الأثر:** إذا فشل exact identity، لا يوجد مسار review-only يعرض الصف العربي
للمستخدم. هذا يفسر لماذا قد ينتهي item إلى `identity_absent` بدل manual review
بمرشح target حقيقي.

**ما يجب اختباره:** English item مع Arabic-only catalog في حالتين: brand alias
موثوق، وbrand غير معروف. يجب أن يظهر الأول فقط وبـ provenance واضح، ولا يجوز
أن ينتج الثاني fuzzy cross-script غير موثوق.

### H3 — parser gap للرموز الملتصقة

**الدليل:** `3AMP` و`3مبول` لا يعطيان نفس attributes التي يعطيها الشكل
المفصول بمسافة؛ القياس الحالي لا يثبت form/pack للصف الصحيح كما هو متوقع.

**الأثر:** بعد إصلاح recall قد يظهر المرشح الصحيح، لكن compatibility قد
يصفه `unproven`. هذا مقبول للمراجعة، لكن يجب ألا يتحول إلى auto-match بسبب
تخفيف gate.

**ما يجب اختباره:** `3AMP`, `3 AMP`, `3AMPS`, `3امبول`, `3 امبول`, `3مبول`
مع صيغ خاطئة مثل `6AMP` و`5قرص` وstrength مفقود.

### H4 — حدود scoring/selection قد تخفي مرشحين إضافيين

**الدليل:** discovery يشترط shared meaningful token وminimum score/margin،
ثم limit 5؛ config الحالي لا يطلب exhaustive candidate list.

**الأثر:** حتى بعد إصلاح identity، قد لا يرى المراجع أكثر من top candidates.
هذه ليست علة الصفين الحاليين، لكنها تعيق مطلب "كل المرشحين المحتملين".

**ما يجب اختباره:** 0، 1، 2، 5، و6 صفوف متشابهة، equal scores، ambiguous
margin، وصفوف variant conflict/unproven. افصل `candidate_count_total` عن
`candidate_count_saved` في كل artifact.

### H5 — احتمال اختلاف artifact عن working tree/config

**الدليل:** run `20260909_1457` تاريخي، بينما working tree يحتوي تغييرات غير
مُلتزم بها في identity/attributes/aliases. لا يجوز استنتاج أن artifact يمثل
بالضبط آخر working-tree code من دون catalog/config/run fingerprint.

**ما يجب اختباره:** إعادة replay read-only على نفس workbook، نفس config، ونفس
input snapshot مع تسجيل commit hash وhash للـ workbook والـ config. لا تستخدم
النتيجة التاريخية وحدها كـ regression oracle.

### H6 — writer truncation ليس السبب الرئيسي

**الدليل:** artifact يعلن total=1 وsaved=1، والـ JSONL options فيها نفس
المرشح الخاطئ. لا يوجد أثر لمرشح صحيح تم إسقاطه أثناء serialization.

**ما يجب اختباره:** حقن قائمة candidates تحتوي 0/1/5/6 عناصر مباشرة في
`_append_excel_target_review_artifacts` والتحقق من header/count/options؛ ثم
اختبار upstream منفصل يثبت أن candidate الصحيح يصل إلى writer.

## نقاط اختبار مطلوبة قبل أي إصلاح

### A. تحميل الصفوف والهوية

- تحميل `محروس1.xlsx` والتحقق من بقاء source rows 2345 و3100، الاسم الخام،
  source file، و`store_product_id` مختلف لكل صف code-less.
- اختبار أن duplicate code أو blank code لا يدمج variants المختلفة.
- اختبار أن `excel_target_row_key` يختلف باختلاف source row/name؛ العقد موجود
  في [`excel_target_review_candidates.py:350-365`](../../src/core/excel_target/excel_target_review_candidates.py:350).

### B. normalization وidentity recall

- assert أن alias lookup لـ `VOLTAREN 3AMP` يعيد الصف 3100 كـ target review
  candidate، وlookup لـ `XITHRONE 500MG 3TAB` يعيد الصف 2345.
- إبقاء الصفوف 3101/3102 و2344/2346 كمرشحين variant منفصلين عند انطباق
  brand، لا استبدالها بصف واحد.
- negative cases: `VOLTAREN 6AMP`, `XITHRONE 500MG 5TAB`، وbrand مختلف لا
  ينبغي أن يرث alias بسبب إزالة واسعة لـ `س` أو attribute tokens.
- التأكد من أن `tawreed_catalog`, `dictionary`, `safe_alias`, وcached
  translation evidence لا تختلط في ranking أو provenance.

### C. review discovery cross-script

- اختبار English query + Arabic-only target row مع alias deterministic واضح.
- اختبار English query + Arabic-only row بلا alias: لا auto-match؛ إما review
  candidate معلّم بدليل review-only صريح أو لا candidate، لكن السلوك يجب أن
  يكون متعمدًا ومغطى باختبار.
- اختبار عدم استدعاء Cohere من discovery نفسه، بما يتسق مع module contract
  في [`excel_target_review_discovery.py:1-7`](../../src/core/excel_target/excel_target_review_discovery.py:1).
- اختبار ترتيب ثابت، tie/ambiguous، score margin، وdistinct source rows.

### D. compatibility وattributes

- `extract_product_attributes` للطلبين والصفين الصحيحين، مع assertions
  منفصلة للـ form/strength/pack/concentration.
- التحقق أن الصف الصحيح، عند إدراجه، يبقى في manual-review حتى لو كانت
  attribute proof ناقصة؛ لا يختفي بسبب rejection.
- negative cases للـ 50/75 MG، 3/6 ampoules، 3/5 tablets، وsyrup مقابل
  tablet.
- اختبار أن `cohere_translation` يبقى review-only في
  `_compatible_identified`، ولا يتحول إلى verified match بمجرد score.

### E. candidate builder والحدود

- تمرير `identified`, `discovery_hits`, وdiagnostics لنفس row والتأكد من
  `_keep_best` وstable row key وعدم تكرار الصف.
- اختبار أن diagnostics لا تقبل `storeProductId` غير موجود في catalog؛ هذا
  guard مقصود في [`excel_target_review_candidates.py:178-183`](../../src/core/excel_target/excel_target_review_candidates.py:178).
- اختبار 6 مرشحين مع limit 5: total المكتشف يجب أن يظل معروفًا، وsaved يجب
  أن يطابق الحد، و`manual_review_required` يجب أن يعتمد على total لا saved.
- اختبار أن candidate الصحيح يحمل `target_key`, `source_file`, source row,
  row key, method, evidence, score, margin, compatibility status/rejection.

### F. artifacts والـ reporting

- تشغيل isolated artifact run على نسخة input/catalog، ثم التحقق من:
  `match_only_summary_<target>.csv`, `match_only_summary_<target>.jsonl`,
  `manual_review_<target>.csv`, و`manual_review_candidates_<target>.jsonl`.
- يجب أن يظهر الصف 3100/2345 في `options` مع اسمه العربي وsource row key؛ لا
  يكفي أن يكون `candidate_count_total > 0` بسبب مرشح آخر.
- التحقق من invariant:

  ```text
  manual_review_required == (candidate_count_total > 0)
  candidate_count_saved <= candidate_count_total
  no target candidate has Tawreed-only supplier/source leakage
  no automatic match has rejected compatibility
  ```

- مقارنة CLI artifact مع `scripts/baraka_coverage_report.py` على نفس snapshot؛
  إذا اختلف candidate set فلابد من تفسيره، لا دمج النتائج تلقائيًا.
- تشغيل `scripts/evaluate_excel_target.py` على before/after CSV فقط بعد وجود
  fixture labels للصفين، مع فصل new review candidates عن automatic matches.

## خلاصة قابلة للتسليم للفريق الذي سيطبق الإصلاح لاحقًا

الحد الأدنى من تعريف النجاح ليس أن يصبح `VOLTAREN 3AMP` matched تلقائيًا.
تعريف النجاح الأول هو أن تصل صفوف `فولتارين 3مبول س جديد` و`زيثرون 3قرص س
جديد` إلى manual-review options مع provenance وrow identity وcompatibility
evidence، وأن تبقى الصفوف المتعارضة أيضًا مرئية عند الحاجة. بعد ذلك فقط يمكن
تقييم ما إذا كان أي صف compatible وحيد يستوفي سياسة automatic matching.

أي إصلاح مقبل يجب أن يعالج identity recall وcross-script discovery/alias
contract معًا، ويختبر parser للرموز الملتصقة، ثم يثبت أن writer يحفظ القائمة
كما وصلت. رفع `manual_review_save_candidate_limit` أو تعديل CSV/JSONL وحده
لن يعيد المرشح المفقود، لأن نقطة الفقد الحالية upstream من serialization.
