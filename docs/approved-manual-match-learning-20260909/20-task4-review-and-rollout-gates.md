# Task 4: مراجعة تنفيذية مستقلة وبوابات الإطلاق

## القرار التنفيذي

**الحالة: BLOCKED قبل أي توسعة cross-language.**

اتجاه Task 4 صحيح، وبعض أجزاء التنفيذ ظهرت بالفعل في working tree: توجد
regression أولية لـ save-cap وأداة report read-only. لكن التنفيذ الحالي لا يحقق
عقد القياس الكامل بعد؛ الأداة لا تتحقق من كل invariants ولا تملك قياسًا حقيقيًا
لـ`C_display`، ومسار القراءة/العرض يستطيع إسقاط صفوف Excel فعلية مختلفة إذا
تشابهت بقية بياناتها.

لا يجوز استخدام زيادة عدد المرشحين الحالية كدليل على تحسن precision أو recall
قبل إغلاق البوابات أدناه.

## نطاق المراجعة

تمت مراجعة الخطة والحدود الفعلية في:

- `16-phase2-candidate-coverage-plan.md`، Task 4 وبوابات القبول.
- `src/cli/commands/cli_order_excel_target.py`، منطق generated/save artifacts.
- `src/core/excel_target/excel_target_review_candidates.py`، row identity والترتيب.
- `src/core/manual_review/manual_review_candidates.py` و
  `src/core/manual_review/manual_review_candidate_store.py`، round-trip.
- `src/ui/manual_review/streamlit_manual_review_page.py`، display والدمج.
- `src/core/excel_target/excel_target_matching.py`، فصل automatic عن review-only.
- `scripts/baraka_coverage_report.py` و`scripts/evaluate_excel_target.py`،
  الأدوات الموجودة حاليًا.
- `tools/report_excel_target_candidate_coverage.py`، أداة Task 4 الحالية،
  وdelta الاختبار في `tests/cli/commands/test_excel_target_manual_review_artifacts.py`.

هذه المراجعة لم تعدّل كود الإنتاج أو `state` أو ملفات الإدخال.

## ما هو مثبت حاليًا

1. في CLI يتم أخذ `all_review_candidates` قبل تطبيق حد الحفظ، ثم:

   - `candidate_count_total = len(all_review_candidates)`.
   - `review_candidates = all_review_candidates[:review_limit]`.
   - الحفظ يتم من القائمة المقصوصة.

   هذا يثبت فصلًا جزئيًا بين `total` و`saved` في مسار Excel-target.

2. كل مرشح يُنتج من `TargetProduct` في الكتالوج المحمّل، ويحمل نظريًا
   `target_key` و`source_file` و`excel_target_source_row` و
   `excel_target_row_key`. دالة `excel_target_row_key` تشمل target والملف ورقم
   الصف وproduct id والاسم، وهذا هو الشكل الصحيح لهوية صف Excel.

3. `_compatible_identified` يرفض حاليًا
   `review_identity` و`review_identity_prefix` و`review_fuzzy`، كما أن
   `_identity_decision` يرفضها أيضًا عند استدعائه مباشرة. توجد اختبارات مباشرة
   لـ `VOLTAREN` و`XITHRONE` تثبت أن `best_match` يظل `None`.

4. ترتيب المرشحين داخل `build_review_candidates` يستخدم tier ثم compatibility
   ثم score/margin ثم row key، وهو أساس جيد للحتمية، بشرط أن يظل row key محفوظًا
   في كل طبقات persistence والعرض.

## النتائج والعوائق

### 1. أداة Task 4 موجودة، لكنها لا تغلق عقد القياس

الملف `tools/report_excel_target_candidate_coverage.py` موجود ويحسب توزيعات
`mean/p50/p95/p99/max`، ويقبل labels اختيارية، ولا يفتح SQLite أو input
workbook. هذا تقدم صحيح، لكنه لا يكفي للقبول للأسباب التالية:

- `scripts/baraka_coverage_report.py` يولد صفوف coverage ويحسب
  `review_candidate_count_total` و`saved`، لكنه لا يقدم histogram/quantiles
  كاملة لـ `p50/p95/p99/max` ولا precision sample مُعنونًا بمصدر label.
- الأداة الجديدة نفسها تستخدم `candidate_count` كـfallback لـ
  `candidate_count_displayed`. في artifact الحالي `candidate_count` هو عدد
  الخيارات المحفوظة، وليس عدد الخيارات التي اختارها UI؛ لذلك قد تعلن الأداة
  `C_display == C_saved` دون أن تكون قد راقبت العرض فعلًا.
- لا تتحقق الأداة من `saved <= total` أو `display <= saved`، ولا تكشف duplicate
  item records؛ `records_by_item` يستبدل record سابقًا بصمت عند تكرار item key.
- لا تسجل catalog fingerprint أو config/discovery/save/display settings، ولا
  تستطيع من artifact-only التحقق من أن row key موجود فعلًا في workbook الحالي.
- `scripts/evaluate_excel_target.py` يقارن تقارير CSV ويطبق بعض فحوص gold/data
  quality، لكنه لا يعيد بناء `C_display` من مسار UI ولا يتحقق من round-trip
  لكل row key.

**الأثر:** توجد الآن طريقة أولية لقياس volume/tail، لكن لا توجد بعد طريقة
قابلة للتدقيق لإثبات candidate recall@N و`C_display` أو سلامة provenance قبل
إضافة قناة cross-language. ولا يمكن فصل تحسن retrieval عن مجرد زيادة عدد
السجلات المحفوظة.

### 2. حد الحفظ موجود، وregression أولية له موجودة لكنها ضيقة

الحد الفعلي في CLI هو `manual_review_save_candidate_limit`، بينما حد discovery
في matcher هو `excel_target_review_candidate_limit`. لذلك توجد ثلاث مراحل يجب
تسميتها صراحة:

```text
C_generated = union الناتج من identity + discovery + diagnostics بعد حدود discovery
C_saved     = options المكتوبة في JSONL/CSV
C_display   = options التي يختارها UI بعد merge/filter/display limit
```

`candidate_count_total` الحالي يساوي `C_generated` بعد حدود discovery، وليس
عدد كل الصفوف الممكنة في الكتالوج. لا يجوز تسميته `catalog universe` في تقرير
recall إلا إذا عُرّف universe بهذه الطريقة وسُجلت حدود discovery.

الاختبار غير المتتبع الحالي يحقن أربعة مرشحين ويثبت `total=4`, `saved=2` و
`len(options)=2`، وهذا يثبت writer path فقط. لا يختبر load/store/UI، ولا
`C_display`، ولا cases الخاصة بالحدود غير الصالحة.

توجد أيضًا نقطة سياسة يجب تثبيتها: `_review_candidate_limit` يحول قيمة `0`
إلى `1` عبر `max(1, ...)`، بينما بعض الأدوات الأخرى تتعامل مع الصفر كتعطيل.
يجب اختيار semantics واحدة واختبارها، لا تركها لاختلاف المسارات.

### 3. فجوة provenance/dedup في القراءة والعرض — blocker

writer يكتب `excel_target_row_key` داخل كل option، لكن deduplication بعد القراءة
لا يستخدمه:

- `load_review_candidates` يبني identity من product id والاسم والمصدر وtarget
  والملف، دون `excel_target_row_key` أو رقم الصف.
- `_load_group_candidates` في Streamlit يكرر الفكرة نفسها، ودون row key.

إذا كان workbook يحتوي صفين فعليين لهما نفس product id والاسم والملف لكن
بـ`source_row_number` مختلف، فهما مرشحان مختلفان حسب العقد، وقد يسقط أحدهما
أثناء load/merge. هذا خطر مباشر على recall بعد الحفظ، ويصبح أكثر احتمالًا عند
توسيع discovery أو cross-language aliases.

**الاختبار الحاجز:** أنشئ optionين بنفس product id/name/source/target، مع
رقمي صف مختلفين، اكتب artifact ثم اقرأه عبر store ومرره إلى UI merge؛ يجب أن
يبقى الخياران، وأن يعاد حساب كل row key من نفس metadata، وألا يحدث dedup إلا
على row key نفسه.

### 4. `ranking_tier` لا يمر عبر round-trip

`ExcelTargetReviewCandidate.to_review_candidate_dict()` يكتب `ranking_tier`،
لكن `ReviewCandidateOption` لا يملك الحقل، و`from_dict()` يسقط الحقول غير
المعروفة. النتيجة أن artifact الخام يحتوي tier، بينما نموذج العرض لا يحتويه.

هذا لا يغير الترتيب الحالي إذا ظل UI يحافظ على ترتيب JSONL، لكنه يمنع تدقيق
الترتيب، ويجعل أي merge أو re-ranking لاحق غير قابل لإعادة الإنتاج أو التدقيق.

**الاختبار الحاجز:** round-trip لكل option يجب أن يحافظ على
`ranking_tier`, `candidate_method`, `score_margin`, `target_key`,
`source_file`, `excel_target_source_row`, و`excel_target_row_key` دون تغيير.

### 5. `C_display` غير ممثل كعداد قابل للتدقيق

UI يطبق `manual_review_display_candidate_limit` بعد تحميل الخيارات، مع إمكانية
إضافة عدد من Streamlit. كما أن `_limit_candidates_by_source` يضمن تنوعًا
مصدرِيًا عند الإمكان. هذا فصل سلوكي مفيد، لكنه لا يكتب أو يعيد `display_count`
ولا يعرض envelope الأصلي الذي يحتوي `candidate_count_total` و
`candidate_count_saved`.

بالتالي لا يمكن من artifact وحده إثبات الفرق بين:

- candidate لم يُولد أصلًا؛
- candidate وُلد ولم يُحفظ بسبب save cap؛
- candidate حُفظ ولم يظهر بسبب display cap أو filter؛
- candidate ظهر ثم اختفى بسبب hide-completed.

يجب أن يظل `C_display` metric مشتقًا ومعلنًا كمرحلة UI، لا أن يُخلط مع
`candidate_count` الموجود في summary.

والأهم أن report tool الحالية لا تلتزم بهذا الفصل: fallback الخاص بـ
`candidate_count_displayed` يقرأ `candidate_count`، فيحوّل saved إلى displayed.
لذلك يجب اعتبار `C_display` **غير مقاس** حتى يتم تسجيله من UI selection أو
تعريف artifact صريح له.

### 6. عدم اتساق tier مع safety policy لـ `cohere_translation`

مسار automatic يرفض `cohere_translation` تحت safe policy، لكن
`ranking_tier` الحالي يعامله ضمن مجموعة tier 0 إذا كانت compatibility مقبولة.
هذا لا يصنع `best_match` بسبب gate الحالي، لكنه قد يجعل دليلًا manual-review
مرفوضًا يتقدم على `review_identity` الموثق في قائمة المراجعة.

قبل cross-language يجب أن تكون كل evidence kinds المرفوضة تلقائيًا مصنفة
review-only في ranking أيضًا، أو يكون لها tier مستقل ومعلن. يجب ألا يوجد
allowlist صامت يجعل evidence kind مرفوضًا تلقائيًا يبدو كـtrusted-compatible
في واجهة المراجع.

### 7. automatic isolation مثبت جزئيًا فقط

الاختبارات الحالية تغطي gate الداخلي وبعض حالات matcher، لكنها لا تثبت العقد
على كل نقاط التأثير:

- `ExcelTargetMatcher.match`.
- `match_item_against_all_targets` و`first_accepted_match`.
- CLI summary/Run DB.
- `_auto_save_excel_target_match` وrebind/approved replay.

يجب أن يكون unknown/future evidence fail-closed: لا يُستخدم لإنتاج
`best_match` أو auto-save حتى لو كانت compatibility `accepted=True`.

## Acceptance tests الإلزامية قبل cross-language expansion

### A. save/display limits

- fixture يولد 8 مرشحين، save limit = 3، display limit = 2:
  - `C_generated == 8`.
  - `C_saved == 3`.
  - JSONL `len(options) == 3`.
  - UI يعرض 2 فقط، ولا يغير ذلك `manual_review_required` أو `C_generated`.
  - `0 <= C_display <= C_saved <= C_generated`.
- matrix منفصلة لـ discovery limit أقل/أكبر من save limit، مع إخراج أسماء
  الحدود في التقرير حتى لا يُفهم total بعد discovery كأنه catalog universe.
- اختبار limits للقيم السالبة، الصفر، والقيم غير الصالحة، مع semantics موحدة
  بين CLI وcoverage report وUI.
- اختبار source diversity يثبت أن display cap لا يتجاوزه، وأن ترتيب الاختيارات
  ثابت عند تساوي score أو اختلاف ترتيب ملفات JSONL.

### B. determinism

- تشغيل matcher مرتين بنفس catalog/config/item ينتج نفس قائمة row keys وmethods
  وtiers وscores؛ يُستبعد فقط الزمن وrun id من hash المقارنة.
- مقارنة workers = 1 وworkers = 4 على نفس الإدخال: نفس matched set، نفس
  review item keys، ونفس ترتيب options/counts.
- equal-score/equal-margin candidates تُرتب دائمًا بالـ`excel_target_row_key`.
- تكرار قراءة نفس JSONL ودمج target files بترتيبات مختلفة لا يغير النتيجة
  الدلالية ولا يسقط physical rows.
- التقرير يسجل `git_sha`, config hash, input hash/catalog fingerprint، وإعدادات
  discovery/save/display، ويرفض المقارنة إذا تغير catalog fingerprint.

### C. provenance وround-trip

- كل option يطابق target catalog الحالي في `target_key`, `source_file`,
  `source_row_number`, و`excel_target_row_key`، ويُعاد حساب row key للتحقق.
- صفان متشابهان في product id/name لكن مختلفان في رقم الصف يبقيان خيارين
  مستقلين بعد writer → store → UI.
- لا يظهر في Excel-target options أي Tawreed source/product/price/availability؛
  أي cross-target diagnostic لا يُقبل إلا إذا حُل إلى صف في catalog الهدف الحالي.
- CSV وJSONL لنفس item يحملان نفس item key وtotal/saved، ولا يوجد duplicate
  item record غير مبرر.
- round-trip لا يفقد `ranking_tier` أو provenance أو candidate method.

### D. review-only isolation

لكل evidence kind من القائمة التالية، أنشئ candidate متوافقًا ظاهريًا واختبر
أن `decision.best_match is None` وأنه لا يحدث auto-save أو rebind:

```text
review_identity
review_identity_prefix
review_fuzzy
english_fuzzy
arabic_fuzzy
cohere_translation
unknown/future discovery_only
```

ثم اختبر في CLI أن:

- automatic matched set لا يزيد بسبب أي من الأدلة السابقة؛
- `matched` و`best_match` لا يُبنيان من option موجود فقط في review artifact؛
- auto-save يقبل فقط evidence kinds المصرح بها للautomatic plane، وunknown
  evidence يفشل مغلقًا؛
- trusted native/dictionary identity ما زال يستطيع automatic match في test
  مستقل، حتى لا يتحول safety gate إلى تعطيل شامل.

### E. report correctness وprecision

أداة Task 4 يجب أن تكون read-only بالنسبة إلى SQLite وinput workbooks، وتكتب
فقط إلى output path يحدده المستخدم. يجب أن تنتج لكل target ثم aggregate:

- `C_generated`, `C_saved`, `C_display` مع mean/p50/p95/p99/max.
- coverage categories وcandidate recall على gold row keys، وليس الاسم أو code
  فقط.
- `recall_generated`, `recall_saved`, و`recall_at_1/@5/@N` مع denominators.
- precision sample مفصول إلى positive/negative وموثق بـlabel source، reviewer،
  adjudication، ووقت التقييم؛ لا يحسب score أو compatibility بدلًا من label.
- automatic verified set قبل/بعد، approved manual overrides منفصلة، وsafety/data
  quality errors.
- zero-denominator وmissing/invalid artifact handling صريح، لا يتحول إلى
  precision أو recall وهمي.
- اختبار subprocess أو monkeypatch يثبت عدم استدعاء translation provider وعدم
  الكتابة إلى manual-review DB أو cache أو input workbook.

### F. gold وnear-negative قبل أي قناة جديدة

- gold row 3100 لـ`VOLTAREN` وrow 2345 لـ`XITHRONE` موجودان في
  `C_generated` و`C_saved` تحت الإعداد الحالي؛ وإذا كان الهدف “يظهر للمراجع”
  يجب أيضًا إثبات وجودهما في `C_display` تحت display limit المعلن.
- gold set يشمل variants للـform/strength/pack والرموز الملتصقة واللاحقة
  `س جديد`.
- near-negative set يشمل short roots، shared prefixes، manufacturer-only suffixes،
  unrelated brands، وnumeric overlap فقط.
- لا تُقبل توسعة إذا تحسن recall مع false positives غير مقاسة أو إذا ارتفع
  `candidate_count_total` tail فوق budget معلن.

## بوابة rollout المقترحة

### Gate 0 — إغلاق Task 4

الحالة الحالية: **FAIL**.

يجب أولًا توسيع regression save-cap لتغطي load/store/UI، وتصحيح report tool
لتفشل عند count inconsistencies ولا تسمي saved بأنه displayed، ثم حل row-key
dedup و`ranking_tier` round-trip وتحديد semantics موحدة للحدود الثلاثة.

### Gate 1 — replay baseline قابل للمقارنة

الحالة المطلوبة:

- نفس input/catalog/config fingerprint في before/after.
- لا mutation في manual-review DB أو translation cache أو input workbook.
- semantic artifact hash متساوٍ عند إعادة التشغيل بنفس الكود والإعدادات.
- p50/p95/p99/max لـ`C_generated`, `C_saved`, `C_display` مسجلة لكل target.

### Gate 2 — correctness وsafety

يجب أن تكون جميع invariants بلا أخطاء:

```text
0 <= C_display <= C_saved <= C_generated
manual_review_required == (C_generated > 0)
every option row key resolves to the loaded target catalog
no review-only evidence produces best_match or auto-save
automatic matched set is unchanged by review-only expansion
```

### Gate 3 — gold/precision budget

يجب أن تكون gold positives مسترجعة داخل المستوى المطلوب، مع precision sample
مراجع بشريًا وnear-negatives مقاسة. تُحدد ميزانية tail والضوضاء قبل القراءة؛
الافتراضي الآمن هو إيقاف rollout عند أي false automatic match، أو provenance
error، أو gold failure، أو تجاوز p95/p99/max للميزانية المعلنة.

### Gate 4 — cross-language feature gate

بعد Gate 0–3 فقط تُضاف قناة target-scoped review-only، خلف feature flag، بلا live
translation أو network، وبـrollback واضح. لا تُرفع automatic thresholds ولا
يُضاف transliteration إلى identity plane في نفس التغيير.

## الخلاصة

الـwriter الحالي يوفر أساسًا جيدًا لفصل generated عن saved، وautomatic gate
يمنع عدة أنواع review-only من إنتاج match. لكن Task 4 لا يمكن اعتباره مقبولًا
بعد: أداة القياس الحالية غير مكتملة، save-cap مختبر في writer فقط،
`C_display` غير قابل للتدقيق،
والأخطر أن load/UI dedup لا يعتمد على row key وقد يسقط صفوفًا صحيحة. لذلك
التوصية التنفيذية هي **عدم بدء cross-language expansion** قبل إغلاق Gate 0 ثم
إثبات Gates 1–3 على replay ثابت وgold/negative set موثق.
