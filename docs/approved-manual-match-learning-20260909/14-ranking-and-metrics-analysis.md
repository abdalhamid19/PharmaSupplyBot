# تحليل زيادة المرشحين المفيدين دون ضوضاء

## الحالة والنطاق

هذا تقرير تحليلي فقط. لم يتم تعديل كود الإنتاج أو إعداداته أثناء إعداده؛ الملف الوحيد المقصود إضافته هو هذا التقرير.

تعتمد الملاحظات على قراءة المصدر الحالي والاختبارات وملفات artifacts، وبالأخص:

- [excel_target_review_candidates.py](../../src/core/excel_target/excel_target_review_candidates.py)
- [excel_target_review_discovery.py](../../src/core/excel_target/excel_target_review_discovery.py)
- [excel_target_matching.py](../../src/core/excel_target/excel_target_matching.py)
- [cli_order_excel_target.py](../../src/cli/commands/cli_order_excel_target.py)
- [manual_review_candidate_store.py](../../src/core/manual_review/manual_review_candidate_store.py)
- [streamlit_manual_review_page.py](../../src/ui/manual_review/streamlit_manual_review_page.py)
- [manual_review_candidates.py](../../src/core/manual_review/manual_review_candidates.py)
- [state/config.yaml](../../state/config.yaml)

تعذر تشغيل subagents إضافيين في هذه الجلسة لأن واجهة استدعاء الـsubagent غير متاحة، رغم وجود subagent مسجل في البيئة. لذلك تم تنفيذ المسارات الثلاثة المطلوبة مباشرةً من المصدر: الاستخراج والترتيب، الحدود والـartifacts، ثم واجهة المراجعة والقياسات.

## القرار التنفيذي المختصر

أقل تغيير قابل للتنفيذ بأمان هو إضافة طبقة pure selection بين build_review_candidates وبين كتابة artifacts، مع إبقاء automatic matching كما هو:

1. تكوين C_universe من كل المرشحين المكتشفين حاليًا، مع الاحتفاظ بالـrow_key وعدم إسقاط أي مرشح بسبب save limit.
2. حساب ranking_tier وattribute_alignment وevidence_strength لكل مرشح.
3. ترتيب deterministic متعدد الطبقات.
4. اختيار C_saved بقاعدة diversity بسيطة: مرشح قوي أولًا، ثم مرشح واحد على الأقل من كل evidence method/source المتاح، ثم ملء باقي المقاعد بالترتيب العام.
5. ترك candidate_count_total = |C_universe| وcandidate_count_saved = |C_saved| منفصلين.
6. جعل UI تعرض saved / total وتستخدم نفس الترتيب، مع تضمين row_key في deduplication.

هذا التغيير لا يحتاج إلى خفض fuzzy thresholds ولا إلى تحويل مرشح review-only إلى automatic match. توسيع الاكتشاف نفسه يجب أن يكون خطوة منفصلة ومقاسة، حتى لا تختلط مشكلة الاسترجاع بمشكلة الترتيب.

## 1. كيف يعمل المسار الحالي

المسار الفعلي في ExcelTargetMatcher.match، من السطور 70 إلى 116، هو:

~~~text
saved approval (اختياري)
    ↓
verified identity + compatibility (قرار automatic فقط)
    ↓
offline discovery
    ↓
review-only identity expansion
    ↓
build_review_candidates
    ↓
CLI save cap → JSONL/CSV/Run DB
    ↓
UI merge/dedup/display cap
~~~

المهم أن review_candidates لا يدخل في _compatible_identified؛ أي أن توسيع قائمة المراجعة لا يرفع صلاحية المطابقة التلقائية بحد ذاته.

### 1.1 build_review_candidates

في excel_target_review_candidates.py، السطور 165 إلى 276، توجد ثلاثة مصادر:

- discovery_hits، وتتحول إلى review_fuzzy أو english_fuzzy.
- identified، وتشمل الهوية الموثقة والهوية review-only.
- diagnostics، مع guard يتأكد أن storeProductId يعود إلى صف من نفس target catalog.

كل صف يتم deduplicate له باستخدام excel_target_row_key، وهذا صحيح لأنه يحافظ على الصفوف المتشابهة ذات source row مختلف.

لكن الاختيار الحالي بعد ذلك هو ترتيب تقريبي بـ:

~~~python
score
identity confidence
product code
product name
~~~

لا توجد أولوية صريحة لـ:

- توافق القوة والشكل والعبوة.
- نوع الدليل.
- تنوع candidate_method.
- تنوع source file أو target scope.
- عدم تكرار نفس العائلة التجارية في كل المقاعد.

دالة _keep_best تستبدل المرشح السابق فقط إذا كان score الجديد أكبر. عند التعادل لا يوجد tie-break مبني على جودة الدليل أو التوافق، بل يبقى المرشح الذي وصل أولًا.

### 1.2 الاكتشاف fuzzy وحدوده

في ExcelTargetReviewDiscoveryIndex.discover، السطور 145 إلى 187، يتم اختيار projection واحدة فقط: عربية أو إنجليزية. هذا يمنع خلط اللغات، لكنه يعني أن query إنجليزية لا يبحث في صف عربي لا يملك trusted_name_en.

الأهم أن _select_scored_candidates، السطور 215 إلى 240، يعيد:

- مرشحًا واحدًا في strong.
- مرشحًا واحدًا في medium.
- مرشحين فقط في ambiguous.

لذلك فإن رفع excel_target_review_candidate_limit من 5 إلى رقم أكبر لا يكفي وحده؛ هذا الحد يقطع الناتج بعد الاختيار، لكنه لا يجعل strong أو medium يعيدان كل المرشحين المؤهلين.

كذلك، شرط medium يطلب أن يكون هناك مرشح medium واحد فقط عبر _is_medium، السطور 448 إلى 464. هذا مفيد لتقليل الضوضاء، لكنه يمنع استدعاء عدة مرشحين قريبين في حالات المراجعة اليدوية.

### 1.3 الحدود الحالية

القيم الفعلية في state/config.yaml، السطور 62 إلى 79، هي:

~~~text
manual_review_save_candidate_limit       = 30
manual_review_display_candidate_limit   = 5
excel_target_review_candidate_limit     = 5
~~~

في cli_order_excel_target.py، السطور 298 إلى 303:

~~~python
all_review_candidates = tuple(result.review_candidates)
review_candidates = all_review_candidates[:review_limit]
candidate_count_total = len(all_review_candidates)
candidate_count = len(review_candidates)
~~~

هذا يفصل save cap عن total، وهو تصميم جيد، لكن candidate_count_total حاليًا هو total بعد حدود الاكتشاف وقواعد الاختيار، وليس عدد كل الصفوف التي كان يمكن فحصها في catalog.

في writer، يتم حفظ candidate_count_total وcandidate_count_saved في CSV/JSONL، وهو مفيد للتدقيق. أما في UI، فـload_review_candidates يعيد options فقط ولا يعيد envelope counts إلى نموذج ReviewCandidateOption؛ لذلك لا يستطيع العرض الحالي إظهار saved/total لكل item دون قراءة envelope منفصل.

## 2. أين تأتي الضوضاء أو خسارة المرشح الصحيح؟

### 2.1 زيادة save limit لا تصلح خسارة retrieval

إذا لم يدخل الصف في discovery_hits أو identified أو diagnostics، فلن تنقذه زيادة save limit. ترتيب التدخل الصحيح هو:

~~~text
retrieval universe → dedup → ranking → diversity selection → save cap → display cap
~~~

### 2.2 score وحده قد يملأ القائمة بنوع واحد

قد تكون عدة صفوف من نفس البراند متشابهة جدًا في النص، فيفوز النوع الذي يعطي score أعلى حتى لو كانت كل النتائج من نفس method أو نفس الملف. في حالة عربية/إنجليزية، قد يظهر مرشح fuzzy قريب ويزيح مرشح review identity، أو يحدث العكس، دون سياسة واضحة.

### 2.3 واجهة العرض لا تعيد الترتيب عالميًا

في render_run_candidates، السطور 226 إلى 242، يتم تحميل المرشحين ثم تطبيق _limit_candidates_by_source. هذه الدالة تضمن مرشحًا أولًا من كل source عندما يكون ذلك ممكنًا، لكنها لا تقوم بـ:

- ranking موحد عبر المصادر.
- quota حسب evidence method.
- عرض candidate_count_total.
- pagination داخل خيارات item الواحد.

كما أن خانة Additional candidates to show يمكنها رفع العرض فوق default config؛ لذلك يجب التمييز في القياس بين configured_display_limit وoperator_display_limit.

### 2.4 dedup في load/UI لا يستخدم row key

في load_review_candidates، السطور 48 إلى 90، وفي _load_group_candidates داخل صفحة UI، هوية option للـdedup تعتمد على product id/name/source/target/source file، ولا تشمل excel_target_row_key أو source row.

هذا خطر مهم: صفان مختلفان في نفس workbook لهما نفس product id/name قد يُحفظان في JSONL، ثم يُعرض أحدهما فقط بعد الدمج. لذلك يجب أن يكون row key جزءًا من identity في كل طبقات persistence وUI، لا في build_review_candidates فقط.

## 3. ranking متعدد الطبقات المقترح

### 3.1 لا تستخدم رقمًا واحدًا كبديل عن السياسة

الأفضل أن يحمل كل candidate حقولًا مشتقة واضحة، ثم يكون الترتيب lexicographic deterministic. مثال السياسة المقترحة:

| الطبقة | الدليل | الاستخدام |
|---|---|---|
| 0 | هوية موثقة + توافق variant مقبول | أعلى أولوية للمراجعة، مع بقاء القرار التلقائي منفصلًا |
| 1 | هوية موثقة لكن variant غير مثبت أو متعارض | مهم جدًا لحالات strength/form/pack المختلفة |
| 2 | review_identity anchored alias | يسترجع الصفوف العربية ذات نفس البراند |
| 3 | review_fuzzy/english_fuzzy/arabic_fuzzy مع brand anchor قوي | discovery-only؛ يعرض للمراجع ولا يثبت identity |
| 4 | diagnostics عالية التشابه بلا هوية كافية | tail محدود فقط، لتجنب الضوضاء |

داخل كل طبقة، يكون الترتيب:

~~~text
attribute_alignment
→ brand_anchor_strength
→ evidence_confidence
→ fuzzy_score
→ score_margin
→ compatibility_bucket
→ stable excel_target_row_key
~~~

يوصى بأن يكون compatibility_bucket واضحًا:

~~~text
compatible             = 3
variant_unproven       = 2
variant_conflict       = 1
unknown                = 0
~~~

لكن لا ينبغي أن يختفي conflict تلقائيًا؛ إذا كان البراند موثقًا فيجب أن يبقى في tail ضمن الحد، لأن المراجع قد يكتشف أن بيانات الطلب أو catalog ناقصة.

### 3.2 تعريف attribute alignment

يحسب alignment من نتيجة validate_product_compatibility ومن attributes المستخرجة، لا من fuzzy text فقط:

~~~text
matched_strength + matched_concentration + matched_form + matched_pack
---------------------------------------------------------------
عدد السمات الصريحة في الطلب
~~~

إذا كانت السمة المطلوبة غير موجودة في candidate، فهي unproven وليست تطابقًا. وإذا تعارضت صراحة فهي conflict. هذه المعلومة يجب أن تستخدم للترتيب ولعرض السبب، لا لتغيير automatic safety gate.

### 3.3 diversity selection

بعد ترتيب كل C_universe، يتم اختيار K = manual_review_save_candidate_limit كالتالي:

1. أضف أفضل مرشح global إذا وجد.
2. أضف أفضل مرشح من كل candidate_method غير ممثل، ما دام ليس duplicate row.
3. أضف أفضل مرشح من كل source file/target scope غير ممثل إذا كانت القائمة ما زالت قصيرة.
4. املأ المقاعد المتبقية بالترتيب العام.
5. طبّق row-key dedup مرة أخيرة.

هذه ليست quota صلبة تمنع أفضل المرشحين؛ هي minimum diversity فقط. فإذا كان كل المرشحين من method واحد، لا يتم إنشاء مرشحين وهميين. وإذا كان أحد methods يحمل مرشحين ضعيفين جدًا، لا يُفرض إلا مرشح داخل minimum evidence floor.

صيغة أبسط للتنفيذ:

~~~python
selected = []
for bucket in ordered_buckets:
    take_best_unseen(bucket)
for candidate in globally_ordered:
    take_best_unseen(candidate)
    if len(selected) == K:
        break
~~~

وتكون bucket مبنية على (candidate_method, target_key, source_file)، مع إزالة source_file من المفتاح إذا كان الهدف هو تنويع methods داخل نفس workbook فقط.

## 4. أقل تغيير قابل للتنفيذ

### المرحلة A: تحسين ranking دون توسيع fuzzy universe

هذه هي النسخة الأقل خطورة:

1. إضافة دالة pure جديدة بجانب build_review_candidates، مثل rank_review_candidates.
2. عدم تغيير automatic matching أو identity normalization.
3. عدم تغيير مصادر الاكتشاف.
4. استبدال ordered = sorted الحالي بطبقتين:
   - ordered_universe: كل candidates بعد dedup.
   - selected_for_save: diversity selection بحد limit فقط عند استدعائه.
5. استخدام نفس function في CLI وUI أو حفظ rank/ranking_tier داخل option حتى لا يعيد UI ترتيبًا مختلفًا.
6. إضافة candidate_method وranking_tier وattribute_alignment وrow_key إلى JSONL option؛ الحقول الجديدة backward-compatible.

الاختبارات الضرورية:

- equal score يخرج بنفس row-key order.
- candidate من method ثانٍ يظهر إذا كان ضمن evidence floor.
- conflict لا يختفي، ولا يتحول إلى automatic match.
- target row مكرر في product id/name يبقى مميزًا بـrow key.
- candidate_count_total >= candidate_count_saved دائمًا.

### المرحلة B: زيادة retrieval بحذر

إذا أثبتت المرحلة A أن المرشح الصحيح غير موجود في C_universe، يتم تعديل discovery فقط:

- strong/medium: السماح بإرجاع top-N المؤهلين بدل top-1، لكن فقط إذا كان هناك brand anchor طويل ومشترك.
- ambiguous: الاحتفاظ بكل المجموعة المتقاربة داخل سقف صغير، مثل 3 أو 5.
- عدم خفض thresholds قبل وجود gold set وقياس precision.
- إبقاء excel_target_review_candidate_limit كحد retrieval، وmanual_review_save_candidate_limit كحد save مستقل.

السبب في فصل المرحلتين أن زيادة retrieval تعالج recall، بينما ranking/diversity يعالجان فائدة أول الخيارات. دمجهما في patch واحد يجعل تفسير أي تغير في النتائج أصعب.

### المرحلة C: توسيع دخول الأصناف إلى manual review

المسار الحالي يضع manual_review_required = candidate_count_total > 0 في cli_order_excel_target.py، السطور 301 إلى 307. هذا مناسب لمنع queue فارغة، لكنه يعني أن identity_absent بلا candidate لا يظهر للمراجع.

التوسيع الآمن المقترح ليس إدخال كل identity_absent، بل إضافة فئة review مستقلة فقط عندما يوجد دليل discovery bounded:

~~~text
identity_absent + high-quality discovery candidate → manual review
identity_absent + no candidate                 → يبقى خارج candidate queue
~~~

وإذا كان الهدف جمع أصناف بلا مرشح لتغذية alias learning، يجب أن تكون queue منفصلة باسم no_candidate_review حتى لا تختلط بالـcandidate precision.

## 5. تصميم artifacts/UI المطلوب

### 5.1 حقول artifact

لكل item في CSV وJSONL يوصى بحفظ:

~~~text
candidate_universe_count
candidate_count_total       # alias واضح لـ universe count إن لم يحدث تغيير schema
candidate_count_saved
candidate_count_displayed   # اختياري، يحسبه UI لا writer إن كان العرض تفاعليًا
ranking_policy_version
retrieval_policy_version
~~~

ولكل option:

~~~text
candidate_method
ranking_tier
attribute_alignment
compatibility_status
compatibility_rejection
identity_evidence_kind
score
score_margin
shared_brand_tokens
excel_target_row_key
excel_target_source_row
~~~

وجود policy_version ضروري حتى يمكن مقارنة run قديم بترتيب جديد دون افتراض أن ترتيب الأرقام متشابه.

### 5.2 UI

الحد الأدنى المفيد في بطاقة item:

~~~text
Showing 5 of 12 saved candidates; universe = 27
~~~

ولكل option يجب إظهار:

- الاسم العربي والإنجليزي إن وجد.
- method/tier.
- compatibility status وسبب الرفض.
- target/file/source row.
- score وmargin عند وجودهما.
- indicator واضح أن المرشح review-only.

يجب أن يكون زر عرض المزيد per item أو pagination داخل item، لا مجرد رقم global يرفع عدد كل البطاقات. وعند دمج Tawreed مع Excel targets يجب أن يكون الترتيب داخل كل source deterministic، ثم يطبق diversity على مستوى البطاقة فقط.

## 6. القياسات

### 6.1 مجموعات القياس

نستخدم ثلاث مجموعات منفصلة:

~~~text
C_universe  = كل الصفوف المكتشفة بعد retrieval وdedup، قبل save cap
C_saved     = الصفوف الموجودة في JSONL/CSV بعد save cap
C_display   = الصفوف الظاهرة فعليًا بعد UI display cap وdedup/pagination
~~~

لا يجوز تسمية C_saved أو C_display بـ“كل المرشحين”.

### 6.2 recall@N

لكل gold item i، نحتاج gold_row_key_i من workbook snapshot نفسه:

~~~text
hit_universe_i = 1 إذا gold_row_key_i ∈ C_universe_i وإلا 0
hit_saved_i    = 1 إذا gold_row_key_i ∈ C_saved_i وإلا 0
hit_display_i  = 1 إذا gold_row_key_i ∈ C_display_i وإلا 0
hit_at_N_i     = 1 إذا gold_row_key_i ضمن أول N بعد ranking وإلا 0
~~~

ثم:

~~~text
Recall_universe = sum(hit_universe) / gold_count
Recall_saved    = sum(hit_saved) / gold_count
Recall@1/@5/@10 = sum(hit_at_N) / gold_count
~~~

يجب نشر النتائج لكل target، ولكل category مثل identity_variant_rejected وidentity_absent وambiguous ثم aggregate؛ aggregate فقط قد يخفي فشل target عربي كامل.

### 6.3 coverage

نحتاج ثلاث نسب:

~~~text
candidate_coverage = items with |C_universe| > 0 / eligible items
saved_coverage     = items with |C_saved| > 0 / eligible items
display_coverage   = items with |C_display| > 0 / eligible items
~~~

ولـmanual-review queue:

~~~text
manual_review_coverage = items entering manual review / eligible items
~~~

يجب فصل eligible items عن items التي لم تدخل replay بسبب --limit أو prevented-items filter.

### 6.4 precision والضوضاء

precision@N لا يمكن حسابها من scores فقط؛ تحتاج gold/adjudication. التعريف المقترح:

~~~text
relevant(candidate) = نفس identity التجارية + لا يوجد تعارض صريح مع variant المطلوب
precision@N = relevant candidates in top N / N displayed candidates
~~~

إذا كانت المهمة هي اختيار variant الصحيح تحديدًا، نستخدم تعريفًا أكثر صرامة:

~~~text
strict_relevant = gold row أو row وافق عليه reviewer لنفس item
strict_precision@N = strict_relevant in top N / N
~~~

ولأن المرشح المتعارض قد يظل مفيدًا لفهم سبب الرفض، ينبغي نشر metric ثانية:

~~~text
review_useful_rate = candidates marked useful by reviewer / displayed candidates
noise_rate = 1 - review_useful_rate
~~~

يجب الإبلاغ عن mean/p50/p95/p99/max لـ|C_universe| و|C_saved|، وليس المتوسط فقط. انفجار p95 هو العلامة الأهم على ضوضاء غير مرئية في المتوسط.

### 6.5 metrics إضافية مفيدة

- MRR: رتبة أول مرشح مفيد.
- nDCG@N: إذا أصبح لدينا درجات relevance متعددة بدل label ثنائي.
- method_share@N: نسبة المقاعد التي يستهلكها كل method.
- duplicate_family_rate: نسبة المرشحين من نفس normalized brand/variant family.
- source_diversity@N: عدد المصادر/الملفات الممثلة في أول N.
- review_time_per_item: بعد توفر قياس UI حقيقي.
- auto_match_delta: يجب أن يظل صفرًا في patch review-only.

## 7. acceptance gates

لا يُقبل ranking جديد إلا إذا تحققت كل الشروط التالية على gold set وnegative set:

1. لا توجد automatic matches جديدة ناتجة عن review_identity أو fuzzy review-only.
2. Recall_universe للـgold لا ينخفض.
3. Recall@5 وRecall@10 لا ينخفضان؛ وإذا تحسنا يجب ألا تنخفض strict_precision@5 تحت baseline بلا تفسير.
4. candidate_count_saved <= manual_review_save_candidate_limit لكل item.
5. candidate_count_displayed <= configured/operator display budget مع تسجيل الفرق بينهما.
6. لا يحدث source leakage بين Tawreed وExcel target.
7. لا يختفي distinct row بسبب dedup في loader/UI؛ row key جزء من identity.
8. الترتيب يتطابق بين replay متكرر وبين item-workers=1 وitem-workers=4.
9. artifacts تظل UTF-8، وCSV/JSONL/Run DB تحمل نفس item keys والعدادات.
10. إذا زادت queue coverage، يظل p95/max والـnoise ضمن budget معلن.

## 8. خطة تنفيذ مقترحة بعد اعتماد التقرير

### Patch 1 — أقل تغيير

- pure ranking function.
- method/tier/attribute metadata.
- diversity selection قبل save cap.
- row-key-aware dedup في candidate loader/UI.
- اختبارات deterministic وlimit وprovenance.

### Patch 2 — زيادة retrieval

- top-N bounded للـstrong/medium discovery.
- gold set لحالات VOLTAREN/XITHRONE وحالات عربية/إنجليزية إضافية.
- مقارنة Recall_universe وRecall@5 وprecision@5 قبل تعديل thresholds.

### Patch 3 — queue coverage

- إدخال identity-absent ذي discovery evidence فقط.
- queue منفصلة لـno-candidate learning إن احتجنا جمع alias proposals.
- dashboard/CSV summary حسب category وmethod.

## الخلاصة

المشكلة ليست “عدد المرشحين” فقط. هناك ثلاث نقاط مختلفة: هل تم اكتشاف الصف أصلًا، هل نجا من save cap، وهل ظهر للمراجع. الإصلاح الأدنى والأكثر أمانًا هو تحسين ranking/diversity والـprovenance أولًا، مع الحفاظ على C_universe وC_saved وC_display كعدادات منفصلة. بعد ذلك فقط نوسع fuzzy retrieval top-N، وبقياس recall@N وcoverage وprecision/الضوضاء على gold set ثابت.
