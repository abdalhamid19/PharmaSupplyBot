# تحليل بيانات baseline: `wardany/20260909_1457`

## نطاق الفحص

هذا تقرير أدلة فقط. لم أعدّل كود الإنتاج، ولم أعدّل إعدادات المطابقة أو قواعد البيانات، ولم أشغّل إصلاحًا أو إعادة تشغيل `order` جديدة. أجريت replay داخل الذاكرة لمسار Excel target بهدف تفسير الـ candidate set فقط، مع تعطيل الاعتماد على القرارات المحفوظة.

الملفات الرئيسية التي فُحصت:

- [سجل الـ run في `order_runs.db`](../../state/order_runs.db) — قراءة SQLite بوضع read-only.
- [قرارات المراجعة اليدوية](../../state/manual_review_decisions.db) — قراءة SQLite بوضع read-only.
- [ملخص Excel target](<../../artifacts/excel-target/البركة شركات/20260909_1457/match_only_summary_البركة شركات.csv>).
- [مرشحو Excel target التفصيليون](<../../artifacts/excel-target/البركة شركات/20260909_1457/manual_review_candidates_excel-target_البركة شركات.jsonl>).
- [مصدر الطلب](<../../data/input/order_items/09092026.xlsx>).
- [الكتالوج الذي استُخدم فعليًا](<../../data/input/excel target/محروس1.xlsx>).
- [ملف اسمه `البركة شركات.xlsx` موجود محليًا](<../../data/input/excel target/البركة شركات.xlsx>)، لكنه ليس مصدر الـ run محل الفحص.

## النتيجة التنفيذية

الـ run المطلوب موجود بالكامل، والصفان الصحيحان موجودان في كتالوج `محروس1.xlsx`. المشكلة ليست في غياب الصفوف من Excel، وليست في حد الحفظ `30` مرشحًا، وليست في أن المرشح الصحيح استُبعد بعد ظهوره. المشكلة حدثت قبل بناء وحفظ قائمة المراجعة:

1. تم تحميل الصفوف الصحيحة من الكتالوج.
2. فهرس الهوية العربي/ثنائي اللغة ربط كل طلب بصف عربي آخر له نفس الاسم الأساسي بعد التطبيع.
3. الصف الصحيح احتفظ بلاحقة/سمات عربية (`س` أو `3مبول س`) فلم يطابق مفتاح alias العربي المستخدم للهوية.
4. اكتشاف المراجعة fuzzy للطلب الإنجليزي بحث في projection الإنجليزية فقط، والصفوف العربية في `محروس1.xlsx` لا تملك `trusted_name_en`.
5. لذلك لم يدخل الصف الصحيح إلى `review_candidates` أصلًا؛ الذي حُفظ هو مرشح واحد خاطئ لكنه صف حقيقي من نفس Excel target.

النتيجة الموثقة: **candidate recall مفقود عند مرحلة discovery/identity، وليس عند مرحلة artifact serialization أو UI display.**

## هوية الـ run وما هو موجود في الـ DB

من جدول `runs` في [state/order_runs.db](../../state/order_runs.db):

| الحقل | القيمة |
|---|---|
| `run_key` | `wardany/20260909_1457` |
| `command` | `order` |
| `execution_mode` | `api` |
| `item_workers` | `1` |
| `total_items` | `2397` |
| `artifact_dir` | `artifacts/order/wardany/20260909_1457` |
| `started_at` | `2026-09-09T11:57:24` |
| `finished_at` | `2026-09-09T12:21:36` |

سجل `run_items` يحتوي لكل من الصنفين صفًا منفصلًا لـ `البركة شركات`:

| الصنف | target status | `manual_review_required` | `candidates_considered` | السبب |
|---|---|---:|---:|---|
| `VOLTAREN 3AMP` | `no-results` | 1 | 1 | `candidate has an unrequested strength` |
| `XITHRONE 500MG 3TAB` | `no-results` | 1 | 1 | `candidate strength is not proven` |

يوجد أيضًا صف Tawreed مستقل لكل منهما؛ في مسار `order` العام أصبح `VOLTAREN 3AMP` و`XITHRONE 500MG 3TAB` `added-to-cart`، وليسَا في ملف `manual_review_20260909_1457.csv`. هذا يفسر الفرق بين نتيجة `order` العامة وملخص Excel target: الأول استخدم Tawreed/قرارات محفوظة، والثاني يعرض فشل المطابقة داخل `البركة شركات`.

جدول `run_candidates` في قاعدة `order_runs.db` يحتوي **0 صفًا**، لأن إعداد `store_candidates` في [state/config.yaml:80](../../state/config.yaml:80) معطّل. لذلك لا يمكن استخدام DB وحدها لمعرفة أسماء المرشحين؛ التفاصيل محفوظة في JSONL الخاص بالـ Excel target.

أما `translation_cache` فيحفظ الدليلين العربيين المطلوبين:

| `normalized_ar` | `en_text` | `hits` |
|---|---|---:|
| `زيثرون 3قرص س جديد` | `Zithrone 3 tablets S New` | 65 |
| `فولتارين 3مبول س جديد` | `Voltaren 3 ampoules SR new` | 84 |

وجود الترجمتين في cache لا يعني أن الصفين دخلا candidate set الخاص بـ Excel target؛ فمسار الـ review الحالي يعتمد على صفوف الكتالوج والهوية المسموح بها، وليس على تحويل الترجمة وحده كمرشح target.

## إثبات وجود الصفوف الصحيحة في المصدر

### مدخلات الطلب

في [09092026.xlsx](<../../data/input/order_items/09092026.xlsx>) ظهرت العناصر التالية:

| ورقة/صف | `item_code` | `item_name` |
|---:|---|---|
| 757 | `73852` | `XITHRONE 500MG 3TAB` |
| 819 | `vol3` | `VOLTAREN 3AMP` |

### كتالوج `محروس1.xlsx` المستخدم في الـ run

الملف يحتوي على 4,489 صفًا محمّلًا، وحقول رأسه هي `الخصم`, `سعر ج`, `الصنف`. لا يوجد فيه code column، ولذلك حُسب `store_product_id` لكل صف كـ hash ثابت من مصدر الصف ورقمه واسمه.

| الطلب | صف المصدر | اسم الصف العربي | السعر | `store_product_id` الناتج |
|---|---:|---|---:|---|
| `XITHRONE 500MG 3TAB` | **2345** | `زيثرون 3قرص س جديد` | 63 | `6a6499c3b66311cce1af9955dc4e717e766233fbe1b535fc7ce93a2e3800ffc2` |
| `VOLTAREN 3AMP` | **3100** | `فولتارين 3مبول س جديد` | 51 | `26fd400fc6537c881ab75c05e6836cacee819189e4c82ae5aed11a659853c9f5` |

وهذان الصفان هما الحد الأدنى المؤكد لما يجب أن يكون ظاهرًا للمراجع: هما نفس الاسم/الشكل/الكمية المقصودة في بيانات الطلب، وموجودان في نفس target workbook الذي استُخدم فعليًا.

## ما ظهر فعليًا في candidate set

### `XITHRONE 500MG 3TAB`

في [ملخص CSV:618](<../../artifacts/excel-target/البركة شركات/20260909_1457/match_only_summary_البركة شركات.csv:618>) وفي [candidate JSONL:75](<../../artifacts/excel-target/البركة شركات/20260909_1457/manual_review_candidates_excel-target_البركة شركات.jsonl:75>) ظهر:

- `candidate_count_total=1` و`candidate_count_saved=1`.
- المرشح: صف المصدر **2344** — `زيثرون  500-- 5قرص` — السعر 86.
- `store_product_id`: `a2b8d3e683c4bbc369853c89ed32289e601e15bb16c4feec484bd0894b727298`.
- السبب: `candidate strength is not proven`.
- `candidate_method=tawreed_dictionary`، مع بقاء `source_kind=excel-target` و`source_file=محروس1.xlsx`.

### `VOLTAREN 3AMP`

في [ملخص CSV:674](<../../artifacts/excel-target/البركة شركات/20260909_1457/match_only_summary_البركة شركات.csv:674>) وفي [candidate JSONL:87](<../../artifacts/excel-target/البركة شركات/20260909_1457/manual_review_candidates_excel-target_البركة شركات.jsonl:87>) ظهر:

- `candidate_count_total=1` و`candidate_count_saved=1`.
- المرشح: صف المصدر **3101** — `فولتارين 50مجم - 20قرص` — السعر 48.
- `store_product_id`: `3538af6add9fe8220c593e97c75eb8b33879986c44314c72bea199b927ae1b5c`.
- السبب: `candidate has an unrequested strength`.
- المرشح صف فعلي من `محروس1.xlsx`، وليس صفًا مسرّبًا من Tawreed؛ `tawreed_catalog` هنا نوع دليل الهوية فقط.

إذن المرشح الصحيح لم يظهر كخيار ثانٍ أو ثالث؛ لم يظهر إطلاقًا في JSONL. الصف الصحيح له row keys مختلفة عن المرشح المحفوظ:

| الصنف | row key الصحيح | row key المحفوظ |
|---|---|---|
| XITHRONE | `affa9ba7e415f471621ba78b5d0bb07fc3f4ae4c569d0ccb33aecfa47ab8afe3` | `853cc4369c4959c353a833cfbaa8e668d96068705e452f884a4defe67bf6ca4e` |
| VOLTAREN | `ac2e06b47eb69155125034180f62cc45e056296b3bcc0288e3174b6b2ab51015` | `90310d3d3ec9eda67785292e90b6a1e6b29532cc67d937750a78d91e4e4fcc17` |

## إعادة بناء السبب من الكود

المسار الحالي واضح في المصادر الأولية:

1. [تحميل Excel](../../src/core/excel_target/excel_target_loader.py:143) يحوّل كل صف غير فارغ إلى `TargetProduct`، و[إنشاء الهوية](../../src/core/excel_target/excel_target_loader.py:262) لا يحذف الصفين 2345 و3100.
2. [بناء فهرس الهوية](../../src/core/excel_target/excel_target_identity.py:110) يبني `target_by_arabic`، ثم يربط صفوف Tawreed بالهدف فقط عند تطابق مفتاح الاسم العربي المطبع ([السطر 117](../../src/core/excel_target/excel_target_identity.py:117) وما بعده). ثم يعيد `identify()` الصفوف المطابقة من `by_tawreed_brand` في [السطر 206](../../src/core/excel_target/excel_target_identity.py:206).
3. في replay الحالي كانت قيم التطبيع الفعلية:

   | صف | الاسم | `normalize_arabic_brand` |
   |---:|---|---|
   | 2344 | `زيثرون  500-- 5قرص` | `زيثرون` |
   | 2345 | `زيثرون 3قرص س جديد` | `زيثرون س` |
   | 3100 | `فولتارين 3مبول س جديد` | `فولتارين 3مبول س` |
   | 3101 | `فولتارين 50مجم - 20قرص` | `فولتارين` |

   لذلك أعاد `identify()` الصف 2344 للطلب XITHRONE والصف 3101 للطلب VOLTAREN.
4. [مسار `ExcelTargetMatcher.match`](../../src/core/excel_target/excel_target_matching.py:89) يستدعي الهوية، ثم يستدعي `review_discovery` ([السطر 111](../../src/core/excel_target/excel_target_matching.py:111)).
5. [اكتشاف المراجعة](../../src/core/excel_target/excel_target_review_discovery.py:191) يختار projection واحدة حسب لغة الطلب. الطلبان إنجليزيان، و`trusted_name_en` للصفوف العربية فارغ؛ لذلك replay أعاد `discovery=[]` للعنصرين.
6. [بناء المرشحين](../../src/core/excel_target/excel_target_review_candidates.py:165) يجمع فقط من `discovery_hits` أو `identified` أو diagnostics التي تشير إلى صف محمّل ([189](../../src/core/excel_target/excel_target_review_candidates.py:189)، [214](../../src/core/excel_target/excel_target_review_candidates.py:214)، [231](../../src/core/excel_target/excel_target_review_candidates.py:231)). بما أن الصفين الصحيحين لم يكونا في أي مصدر من هذه المصادر، لم يكن هناك مسار لاحق يمكنه إضافتهما.
7. حد الحفظ في [state/config.yaml:61](../../state/config.yaml:61) هو 30، وحد discovery هو 5 في [state/config.yaml:72](../../state/config.yaml:72). بما أن الإجمالي الفعلي كان 1 فقط، لا يوجد دليل على truncation.
8. الـ CLI يحسب `candidate_count_total` من كل `result.review_candidates` قبل قص المرشحين وحفظهم في [cli_order_excel_target.py:298-303](../../src/cli/commands/cli_order_excel_target.py:298)، لذلك الرقم 1 يصف فقدًا upstream لا فقدًا أثناء الكتابة.

## تفريق ملفي Excel المتشابهين

الـ run يستخدم `محروس1.xlsx`؛ ذلك ظاهر في `candidate_source_file` و`matching_source_label` داخل artifacts. أما `البركة شركات.xlsx` الموجود حاليًا فله رأس مختلف: `شركات `, `سعر ج`, `الكود`, `الصنف`. إعداد target الحالي يتوقع `الخصم` بدل `شركات `، ولذلك replay للملف الثاني بالـ config الحالي يفشل عند column resolution. لا يصح استخدامه كبديل صامت لمصدر run 1457.

هذه نقطة reproducibility مهمة: يجب إعادة الفحص على `محروس1.xlsx`، أو تسجيل إعداد mapping مستقل إذا كان المقصود أصلًا هو الملف الآخر.

## الآثار الناقصة أو غير الكافية

- **موجود:** run metadata، target CSV/JSONL، order CSV/JSONL، DB، source workbook، input workbook، وtranslation cache.
- **غير موجود:** trace وسيط يثبت كل صفوف `target_by_arabic` أو كل نتائج `review_discovery`؛ تمت إعادة بنائه من الكود والكتالوج.
- **غير محفوظ في DB:** أسماء المرشحين على مستوى الصف؛ `run_candidates` فارغ بسبب `store_candidates=false`.
- **غير محفوظ بالكامل:** سطر CLI الأصلي بكل arguments؛ جدول `runs` يحفظ المصدر العام للطلب وmetadata، لا target paths الكاملة. تم استنتاج target file من artifacts.
- **غير متاح كدليل مستقل:** candidate artifact خاص بالـ order العام للصنفين، لأنهما لم يكونا manual-review في Tawreed path؛ الدليل الصحيح هنا هو target artifact و`run_items` الخاص بـ `البركة شركات`.

## طريقة إعادة الإنتاج الآمنة

لاستخدام نفس الحالة دون تعديل production state:

1. استخدم `state/config.yaml` و`data/input/excel target/محروس1.xlsx` مع `source_file="محروس1.xlsx"`.
2. حمّل `Item("73852", "XITHRONE 500MG 3TAB", 1)` و`Item("vol3", "VOLTAREN 3AMP", 1)`.
3. أنشئ `ExcelTargetMatcher("البركة شركات", catalog, use_saved_approvals=False)` داخل عملية مؤقتة.
4. اطبع لكل عنصر: `identity_index.identify(name)`، و`review_discovery.discover(...)`، و`match(...).review_candidates`، مع أرقام الصفوف والأسماء.
5. النتيجة المتوقعة في baseline الحالي: هوية واحدة للصف 2344 أو 3101، discovery فارغ، وreview candidate واحد غير صحيح.

أقرب script تشخيصي موجود هو [scripts/baraka_coverage_report.py](../../scripts/baraka_coverage_report.py)، ويستخدم public matcher seam ويكتب CSV/JSONL. لكن إعادة إنتاج هذه الحالة بدقة يجب أن تكون approval-disabled وفي artifact directory معزول؛ أما `trace_one_item.py` و`findbest.py` و`debug_concor.py` فهي أمثلة hard-coded قديمة وليست replay مباشرًا لهذين الصنفين.

## بصمات الملفات التي فُحصت

| الملف | SHA-256 |
|---|---|
| `09092026.xlsx` | `9AAFAD88FA3933B2950FAAA910A81BA6C678EBCE1C0806DE6CA3A502BD6923F8` |
| `محروس1.xlsx` | `CC50AC5833483105C620D62CE820166F93BCC985405ACD8B9430FD2ABE6F7` |
| `البركة شركات.xlsx` | `DEEED3782B91BFA0238507E1EC7F6D8DB2E6E85C1245CC7C9AD661260B89CFAD` |
| `match_only_summary_البركة شركات.csv` | `23A71972BBB9C1226EFE4044FB48E4D380B43A2618940A6A2B9BF0A2739122E9` |
| `manual_review_candidates...jsonl` | `44873555C6FD1CAD0B828E619A1B4A4967275DD2825B27E4C1CFD471E25ADE05` |

**الخلاصة:** الأدلة الحالية كافية لإثبات أن `VOLTAREN 3AMP` و`XITHRONE 500MG 3TAB` كان ينبغي أن يعرضا على الأقل صفّي `فولتارين 3مبول س جديد` و`زيثرون 3قرص س جديد` من `محروس1.xlsx`، وأن سبب عدم ظهورهما هو فقد candidate recall في identity/discovery قبل الحفظ. لا يوجد في هذا التقرير أي إصلاح أو تغيير سلوكي مُنفّذ.
