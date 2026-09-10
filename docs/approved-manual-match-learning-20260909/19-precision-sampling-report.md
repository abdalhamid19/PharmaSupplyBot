# مراجعة مستقلة لعينة precision/gold/near-negative

تاريخ المراجعة: 2026-09-10

## نطاق المراجعة

هذه مراجعة قراءة فقط للـ artifacts الموجودة، ولا تعدّل كود الإنتاج أو `state` أو
ملفات الإدخال. تمت مقارنة:

- الوضع التاريخي: `artifacts/excel-target/البركة شركات/20260909_1457/`
- الوضع الحالي الذي يحتوي على الصنفين محل السؤال:
  `artifacts/excel-target/البركة شركات/20260910_1243/`
- عينة تشغيل حالية منفصلة للقيصر:
  `artifacts/excel-target/القيصر شركات/20260910_1233/`

التحليل اعتمد على `match_only_summary_*.csv` وعلى
`manual_review_candidates_*.jsonl`. تم تثبيت snapshots الحالية بالـ SHA-256
التالي حتى يمكن إعادة التحليل على نفس البيانات:

| Snapshot | الملف | SHA-256 |
|---|---|---|
| تاريخي/البركة | `20260909_1457/match_only_summary_البركة شركات.csv` | `23A71972BBB9C1226EFE4044FB48E4D380B43A2618940A6A2B9BF0A2739122E9` |
| تاريخي/البركة | `20260909_1457/manual_review_candidates_excel-target_البركة شركات.jsonl` | `44873555C6FD1CAD0B828E619A1B4A4967275DD2825B27E4C1CFD471E25ADE05` |
| حالي/البركة | `20260910_1243/match_only_summary_البركة شركات.csv` | `45B081181EC49BCA66DDCB0712C8A240454B2515A1333EDCA45A1AC0111BC15A` |
| حالي/البركة | `20260910_1243/manual_review_candidates_excel-target_البركة شركات.jsonl` | `39019C60BBC6168B481EFA34D6DED79969CF3126094E8C79F0946E308F242125` |
| حالي/القيصر محدود | `20260910_1233/match_only_summary_القيصر شركات.csv` | `90EF310B67355F0965962CE303C7121B828C8863233C448A702C144D7C215BAE` |
| حالي/القيصر محدود | `20260910_1233/manual_review_candidates_excel-target_القيصر شركات.jsonl` | `49C0F3390B44F0A6ACE725538A34648A21F476D667506BB888AFA2DCEDB8E9F9` |

## الفرق بين candidate recall وprecision

- **Candidate recall/coverage:** هل ظهر الصف الصحيح أصلًا داخل اتحاد المرشحين
  للصنف؟ يلزم وجود gold row موثوق حتى نحسبه. وجود المرشح في JSONL وحده لا يثبت
  أنه صحيح.
- **Precision:** من المرشحين الذين تمت تسميتهم فعليًا، كم واحدًا هو الصف الصحيح؟
  الصيغة المقترحة هي:

  `precision_labeled = عدد المرشحين ذوي label=P / عدد المرشحين ذوي label=P أو N`

  المرشح `U` غير المحسوم لا يدخل البسط ولا المقام، ولا يجوز اعتباره negative
  لمجرد أن matcher رفضه آليًا.
- **Manual-review coverage:** عدد مجموعات الأصناف التي دخلت قائمة المراجعة. هذا
  مقياس لاتساع الطابور وليس precision ولا recall.

لا يوجد في هذه snapshots label بشري كامل لكل المرشحين؛ لذلك لا أقدم رقم
precision. كما أن `compatibility_status` و`candidate_method` و`ranking_tier`
أدلة matcher وليست gold labels.

## ملاحظات قابلة للتحقق من artifacts

| النطاق | صفوف summary | مجموعات manual-review | مجموع المرشحين | p50 للمجموعة | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| تاريخي/البركة 1457 | 799 | 115 | 155 | 1 | 2 | 3 | 4 |
| حالي/البركة 1243 | 799 | 108 | 221 | 2 | 4 | 8 | 11 |
| حالي/القيصر 1233 | 100 | 16 | 26 | 2 | 3 | 4 | 4 |

الـ percentiles أعلاه محسوبة على `candidate_count_total` لمجموعات المرشحين، لا
على كل صفوف summary. تشغيل القيصر `1233` محدود بـ100 صنف، ولذلك لا يصح استخدامه
كمقارنة كاملة مع التشغيل التاريخي أو استنتاج غياب صنف منه.

في البركة الحالية، توزيع طرق المرشحين هو:

- `review_identity`: 34 مرشحًا.
- `review_identity_prefix`: 107 مرشحين.
- الطرق القديمة/الأخرى (`tawreed_dictionary`, `cached_cohere`,
  `cached_translation`): 80 مرشحًا.

التغيير الأساسي هو اتساع الاتحاد المرئي، خصوصًا في alias anchored؛ لكنه رفع
ذيل حجم المجموعة من max=4 إلى max=11. هذا سبب إضافي لقياس precision والضوضاء
قبل خفض أي threshold أو إضافة transliteration أوسع.

## الصنفان محل البلاغ

في snapshot التاريخي `20260909_1457`:

- `VOLTAREN 3AMP` كان له مرشح واحد فقط: row 3101، وهو
  `فولتارين 50مجم - 20قرص`؛ الصف المتوقع row 3100 لم يكن ظاهرًا.
- `XITHRONE 500MG 3TAB` كان له مرشح واحد فقط: row 2344، وهو
  `زيثرون 500-- 5قرص`؛ الصف المتوقع row 2345 لم يكن ظاهرًا.

في snapshot الحالي `20260910_1243`:

| الصنف | عدد المرشحين | الصف المتوقع الظاهر | method | حالة matcher |
|---|---:|---|---|---|
| `VOLTAREN 3AMP` | 8 | row 3100: `فولتارين 3مبول س جديد` | `review_identity` | review-only، `candidate pack is not proven` |
| `XITHRONE 500MG 3TAB` | 3 | row 2345: `زيثرون 3قرص س جديد` | `review_identity` | review-only، `candidate strength is not proven` |

هذه نتيجة **candidate recall إيجابية مبدئية** مبنية على سياق البلاغ والصفوف
المعروضة. لا تتحول إلى gold label نهائي إلا بعد أن يؤكد مراجع بشري أن الصف
يطابق الاسم والـ form والـ strength والـ pack المطلوبين.

## gold seeds وnear-negatives المقترحة

الآتي إطار labeling، وليس labels مسجلة بالفعل. الرمز `P?` يعني gold seed
مقترحًا يحتاج تأكيدًا، و`N?` near-negative مقترحًا يحتاج تأكيدًا، و`U` يظل
غير محسوم حتى يراجع الإنسان الدليل.

| item | مرشح P? | near-negatives المقترحة | سبب إدراجها |
|---|---|---|---|
| `VOLTAREN 3AMP` | row 3100، `فولتارين 3مبول س جديد` | row 3102 (6 أمبول)، row 3101 (أقراص 50mg)، rows 3098/3099/3103/3104/3105 | نفس العلامة مع pack مختلف أو form/strength مختلف؛ hard negatives مفيدة ضد prefix-only |
| `XITHRONE 500MG 3TAB` | row 2345، `زيثرون 3قرص س جديد` | row 2344 (5 أقراص)، row 2346 (شراب 25ml) | نفس العلامة، لكن pack أو form مختلف |
| `VOLTAREN 6AMP`، manual-review إضافية | row 3102، `فولتارين 6امبولة شركه` | row 3100 ثم باقي صفوف VOLTAREN | sibling control لاختبار أن 3 و6 أمبول لا يختلطان |
| `XITHRONE 200MG SUSP 25ML`، manual-review إضافية | row 2346 محتملًا | rows 2344 و2345 | sibling control لاختبار الفصل بين الشراب والأقراص |
| `VOLTAREN EMULGEL 25 GM`، manual-review إضافية | لا يوجد P? من هذه snapshot | row 3105، `فولتارين جيل وسط 50جم س ج`، ويظل `U/N?` حتى يثبت variant | يمنع تحويل مرشح نفس العلامة إلى positive بلا صف 25gm مطابق |

لا أستنتج صحة row 3102 أو row 2346 من الاسم وحده؛ هما gold seeds مقترحة
لأنهما المرشح الطبيعي في sibling manual-review، ويجب تأكيدهما بنفس إجراء
المراجعة.

## تعريف labels وإجراء adjudication

لكل زوج `(item_key, excel_target_row_key)` يسجل المراجع label واحدًا:

- `P`: نفس المنتج المطلوب، مع تطابق brand وform وstrength وpack/concentration
  عندما تكون هذه الحقول معروفة في الطلب.
- `N_variant`: نفس brand/identity لكن variant مختلف، مثل 3 مقابل 6 أمبول أو 3
  مقابل 5 أقراص.
- `N_prefix`: تشابه prefix أو brand فقط دون تطابق المنتج.
- `U`: الدليل غير كافٍ أو النص لا يثبت variant؛ لا يستخدم لحساب precision.
- `E_stale`: الصف غير موجود في catalog الحالي أو provenance غير صالح؛ يفصل عن
  precision الحالي ولا يعاد تفسيره كـnegative.

مصدر gold المقبول، بالترتيب:

1. تأكيد بشري موثق للصف الحالي، مع `target_key`, `source_file`,
   `excel_target_source_row`, و`excel_target_row_key`.
2. قرار manual approval موثق ومطابق لنفس catalog fingerprint والصف.
3. مستند/كتالوج مرجعي يثبت الاسم والـ form والـ strength والـ pack، ثم مراجعة
   بشرية.

لا يصح استخدام `matched_name` أو `score` أو `ranking_tier` كمرجع gold. يراجع
مراجعان مستقلان كل مجموعة، ويستخدم مراجع ثالث عند الاختلاف. تحفظ أسباب الحكم
والدليل، لا label فقط.

## عينة قابلة للتكرار

### 1. عينة إلزامية audit set

تدخل كل المرشحات في المجموعات الخمس التالية، وعددها الحالي 23 مرشحًا:

- `73451::XITHRONE 200MG SUSP 25ML`
- `73852::XITHRONE 500MG 3TAB`
- `VOL3::VOLTAREN 3AMP`
- `VOL6::VOLTAREN 6AMP`
- `74306::VOLTAREN EMULGEL 25 GM`

هذه عينة purpose-built وليست تقديرًا غير متحيز للـprecision؛ لأنها تتعمد
إدخال الصنفين محل البلاغ وكل sibling variants.

### 2. عينة estimation set من باقي البركة

تستخدم snapshot `20260910_1243`، وتعمل على مستوى المجموعة لا على مستوى الصف
المفرد حتى لا تتكرر نفس العائلة بصورة مضللة. لكل مجموعة تحدد:

1. `evidence`: `anchored_exact_present` أو `anchored_prefix_only` أو
   `legacy_or_translation`.
2. `compatibility`: `compatible_only` أو `rejected_only` أو `mixed`.
3. `size`: `singleton` إذا كان `candidate_count_total=1` وإلا `multi`.
4. `stable_key = item_key + "|" + target_key + "|" + source_file`.
5. `rank = SHA256("precision-sample-v1|" + stable_key)` بترميز UTF-8.
6. ترتيب تصاعدي حسب `rank` واختيار أول quota من كل طبقة.

الـquota المقترح هو 26 مجموعة غير focus، ثم label كل خياراتها، فيصبح المجموع
التشغيلي 31 مجموعة و75 مرشحًا مع الـaudit set. توزيع الـ26 غير focus:

| الطبقة | عدد المجموعات في population | quota |
|---|---:|---:|
| exact anchored، rejected، singleton | 3 | 3 |
| exact anchored، rejected، multi | 13 | 5 |
| exact anchored، mixed، multi | 6 | 2 |
| prefix-only، rejected، singleton | 14 | 5 |
| prefix-only، rejected، multi | 13 | 5 |
| prefix-only، mixed، multi | 9 | 2 |
| legacy/translation، rejected، singleton | 16 | 2 |
| legacy/translation، rejected، multi | 13 | 2 |
| **الإجمالي** | — | **26** |

الطبقات التي لا تظهر في snapshot الحالية (`mixed/singleton` لبعض الأدلة)
تظل quota=0 ولا تستبدل آليًا بطبقة أخرى. عند إعادة التشغيل على snapshot جديدة
يُعاد حساب population ويفضل إبقاء نفس القاعدة والـseed، مع تسجيل أي طبقة لم تعد
موجودة.

### 3. طريقة حساب القياس بعد labeling

- يحسب `precision_labeled` لكل طبقة ولكل `candidate_method`، مع عدد `P`, `N`,
  `U`, و`E`.
- يحسب `group precision@1` و`candidate recall@1/@3/@5/@all` للصنف ذي gold row
  معروف.
- يحسب recall على denominator واضح: الأصناف التي أكد المراجع أن gold row لها
  موجود في catalog الحالي. الأصناف التي لا تملك gold أو catalog row لا تدخل
  denominator بدل اعتبارها miss.
- للعينة الطبقية، لا يدمج precision الكلي بمتوسط بسيط إذا اختلفت احتمالات
  الاختيار. يستخدم weighted estimate حسب حجم الطبقة، ويعرض أيضًا كل طبقة
  منفردة.
- يعرض Wilson interval أو exact binomial interval فقط بعد وجود labels؛ لا يعرض
  interval مبنيًا على `score` أو على افتراض أن المرشح الأول صحيح.

## ضوابط تمنع التحيز أو التسرب

- لا يستخدم قرار matcher نفسه كـgold؛ وإلا أصبح القياس اختبارًا لنفس القاعدة.
- لا يخلط snapshot `20260910_1233` للقيصر مع population البركة؛ فهو 100 صنف
  فقط. يجب تشغيل full comparable replay قبل تعميم النتيجة على القيصر.
- لا يخلط `candidate_count_total` مع `candidate_count_saved` أو المعروض؛ يجب
  labeling من JSONL الكامل، ثم التأكد أن `total >= saved >= displayed`.
- يحفظ row provenance كاملًا، لأن رقم الصف وحده لا يكفي إذا تغير workbook.
- يحفظ label snapshot منفصلًا عن matcher artifacts، مع catalog fingerprint؛
  approval قد يصبح stale عند تبديل target workbook.
- لا تتحول المرشحات الجديدة إلى automatic match بسبب كونها `review_identity`
  أو `review_identity_prefix`.

## الحكم المستقل والتوصية

التحسين الحالي يعالج **جذر مشكلة الاستدعاء** في المثالين: الصفان 3100 و2345
أصبحا داخل قائمة المرشحين الحالية بعد أن كانا غائبين تاريخيًا. كما أن القائمة
تعرض variants ذات صلة بدل مرشح واحد فقط. لكنه لم يثبت بعد أن توسيع القائمة حافظ
على precision؛ بل تظهر إشارة مخاطرة قابلة للقياس: p99 ارتفع من 3 إلى 8 وmax من 4
إلى 11 في مجموعات البركة.

التوصية هي تنفيذ labeling للعينة الإلزامية أولًا، ثم estimation set بالـseed
والـquota أعلاه. لا أوصي بتوسيع fuzzy/transliteration أو تغيير thresholds قبل
توثيق `P/N/U`، وقياس precision الطبقي وrecall@k، وفحص near-negatives الخاصة
بـ3/6 أمبول و3/5 أقراص.
