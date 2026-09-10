# مراجعة السلامة المستقلة لمسار review-only

تاريخ المراجعة: 2026-09-10

## النطاق والحكم

هذه مراجعة قراءة فقط للكود والاختبارات المرتبطة بالأدلة التالية:

```text
review_identity
review_identity_prefix
review_fuzzy
cohere_translation
```

تمت مراجعة فصل automatic match عن manual-review candidates، وحفظ الـartifacts،
تحميلها، ومسار عرضها في واجهة المراجعة. لم يتم تعديل كود الإنتاج أو الاختبارات
أو `state` أثناء هذه المراجعة.

الحكم الحالي: **الحاجز الأساسي موجود، لكن safety gate غير مكتمل قبل أي
cross-language expansion**.

السبب الرئيسي أن المسار الطبيعي يمنع الأدلة review-only من إنتاج `best_match`،
لكن الحاجز مبني جزئيًا على denylist للأنواع المعروفة، وليس على allowlist مغلقة
للأدلة المسموح بها. كما أن العزل الكامل عبر CLI ثم JSONL ثم loader ثم UI غير مثبت
لكل الأنواع، ووسم بعض الأدلة review-only غير ظاهر بوضوح أثناء اختيار المراجع.

## ما تم التحقق منه

### 1. الحاجز الطبيعي داخل matcher

في `src/core/excel_target/excel_target_matching.py`:

- `_compatible_identified` يرفض `cohere_translation` قبل فحص compatibility.
- يرفض صراحة `review_identity` و`review_identity_prefix` و`review_fuzzy`.
- `ExcelTargetMatcher.match` لا يستدعي `_identity_decision` إلا للمرشح الذي
  اجتاز قائمة الأدلة المقبولة في ذلك المسار.
- الأدلة anchored الجديدة تذهب إلى `review_candidates`، ولا تستبدل
  `decision.best_match`.
- الـmanual approval المحفوظ له مسار منفصل (`manual_review_rebound`) ومقيّد
  بـ`matching_source` و`excel_target_key` و`source_file` و`source_row` و
  `excel_target_row_key`. هذا استثناء مقصود بعد فعل بشري صريح، وليس promotion
  تلقائيًا لمرشح review-only.

### 2. فصل المرشح عن الصف المستهدف

في `excel_target_review_candidates.py`:

- كل candidate يجب أن يحل إلى صف داخل catalog الحالي.
- `excel_target_row_key` يتضمن target وsource file ورقم الصف والـproduct id
  والاسم، لذلك لا يفترض أن product code وحده يعرّف الصف.
- `review_identity` أعلى من `review_identity_prefix` وfuzzy في ترتيب قائمة
  المراجعة، ولا يُستبدل بمرشح fuzzy ذي score رقمي أعلى لنفس الصف.
- `ranking_tier` محفوظ في option model، وتعديلات round-trip الحالية تحفظ
  `excel_target_row_key` و`tier` في loader/UI dedup.

### 3. الـartifacts والـtests الحالية

الاختبارات الحالية تغطي:

- رفض `review_identity` في `_compatible_identified` ورفضه عند استدعاء
  `_identity_decision` مباشرة.
- إبقاء `VOLTAREN` و`XITHRONE` في قائمة review، بما في ذلك حالة عدم وجود صف
  عربي bare مطابق.
- إبقاء مرشح anchored عند collision مع fuzzy أعلى score.
- دخول identity-absent إلى manual review إذا وجد bounded discovery candidate.
- بقاء identity-absent بلا candidate خارج queue.
- فصل `candidate_count_total` عن `candidate_count_saved` في writer.
- منع legacy manual approval من فرض Excel-target match، مع السماح فقط بالـscoped
  approved match الصحيح.
- بقاء `cohere_translation` وcached Cohere في manual review في الاختبارات
  الحالية.

تم تشغيل المجموعة التالية دون تعديل ملفات المشروع:

```powershell
& '.venv\Scripts\python.exe' -m pytest `
  tests\core\excel_target\test_baraka_safe_matching.py `
  tests\core\excel_target\test_excel_target_candidate_recall.py `
  tests\core\excel_target\test_excel_target_review_candidates.py `
  tests\cli\commands\test_excel_target_manual_review_artifacts.py `
  tests\ui\manual_review\test_streamlit_manual_review.py -q
```

النتيجة: `69 passed, 2 subtests passed`.

## الملاحظات والمخاطر المتبقية

### R1 — الحاجز الداخلي ليس fail-closed بالكامل

`_compatible_identified` يرفض الأنواع المعروفة، لكن `_identity_decision` يرفض
حاليًا أنواع `review_*` فقط. إذا استُدعي مباشرة بــ`cohere_translation` فسوف
ينشئ `best_match` بدل أن يرفضه. وبالمثل لا يوجد رفض عام لـunknown/future
evidence، كما أن `manual_review` موجود في `IdentityKind` لكن سياسة دخوله إلى
automatic plane غير صريحة.

في المسار الطبيعي الحالي لا يظهر هذا كـautomatic match لأن `_compatible_identified`
يحجب Cohere قبل الوصول إلى `_identity_decision`، لكنه يظل ثغرة دفاعية ضد أي
caller جديد أو توسعة مستقبلية. المطلوب قبل التوسع هو allowlist مغلقة للأدلة
automatic، أو اختبار fail-closed صريح لكل نوع غير مسموح.

### R2 — `cohere_translation` مصنّف review-only في القرار، لكن ليس بوضوح في كل
طبقات العرض

الـmatcher يمنع Cohere من automatic match، لكن ترتيب المرشحين يعامل
`cohere_translation` ضمن tier موثوق نسبيًا، ويحوّله إلى `cached_cohere`. في
واجهة الاختيار يوجد وسم `Review-only` صريح لـ`review_fuzzy` فقط؛ أما
`review_identity` و`review_identity_prefix` و`cached_cohere` فيظهر نوع الدليل في
provenance caption، لكن ليس بالضرورة في نص خيار radio نفسه.

هذا ليس promotion آليًا بحد ذاته، لكنه قد يجعل المرشح review-only يبدو للمراجع
كأنه verified identity، خصوصًا إذا تم توسيع القناة لاحقًا.

### R3 — العزل الكامل من artifact إلى UI غير مثبت لكل evidence kind

الاختبارات الحالية تثبت أجزاء منفصلة، لكنها لا تثبت لكل نوع من الأنواع الأربعة
السلسلة التالية في اختبار واحد:

```text
matcher result
  -> CLI summary/JSONL
  -> load_review_candidates
  -> UI grouping/display
  -> no automatic save
```

كما أن `load_review_candidates` يتجاوز JSONL غير الصالح أو option غير القابل
للتحويل بدل إصدار safety/data-quality failure؛ هذا يحمي من crash لكنه قد يخفي
فقدان مرشح أو provenance من تقرير المراجعة.

### R4 — `C_display` غير مقاس كأثر مستقل

الـsummary والـJSONL يميزان generated عن saved، لكن display limit في Streamlit
يطبق لاحقًا. لا يوجد حاليًا artifact مستقل يثبت عدد الخيارات التي ظهرت فعلًا
للمراجع، ولا اختبار يثبت دائمًا:

```text
0 <= C_display <= C_saved <= C_generated
```

لذلك لا يمكن اعتبار وجود row في generated أو saved دليلًا على أنه ظهر للمراجع
فعليًا تحت display limit.

### R5 — prefix expansion تحتاج negative safety set قبل التوسعة

`_review_targets_for_alias` تسمح بصف عربي exact أو بصف يبدأ بالـnormalized
Arabic review brand. هذا يعالج حالة `فولتارين 3مبول س جديد`، لكنه يفتح احتمال
زيادة الضوضاء مع shared prefixes أو أسماء قصيرة أو suffix خاص بالشركة. لم تصبح
هذه false positives مثبتة من الكود وحده، ولذلك يجب إغلاقها باختبارات near-negative
قبل إضافة cross-language channel أو خفض threshold.

### R6 — live translation موجود في التشغيل متعدد الأهداف

`run_excel_target_match_only_multi` يمرر `allow_live_translation=True`. الحاجز
الحالي يمنع نتيجة `cohere_translation` من automatic match، لكن لا يوجد اختبار
طرفي يثبت أن استدعاء provider في هذا المسار لا يغيّر automatic matched set ولا
ينشئ auto-save. يجب فصل اختبار network/provider عن اختبار review discovery؛
cross-language review channel الجديدة يجب أن تبقى offline وtarget-scoped.

## Acceptance tests المتبقية قبل cross-language expansion

لا يبدأ Gate 4 قبل نجاح البنود التالية. كل الاختبارات يجب أن تستخدم catalog وDB
وinput workbook مؤقتة أو mocks، وألا تكتب إلى `state` الحقيقي.

### A. Fail-closed automatic evidence contract

أضف اختبارًا parameterized للأنواع التالية:

```text
review_identity
review_identity_prefix
review_fuzzy
cohere_translation
manual_review
unknown_future_evidence
```

لكل نوع:

1. مرره إلى `_compatible_identified` مع compatibility تبدو مقبولة، وتأكد أنه لا
   يدخل automatic accepted set.
2. مرره إلى `_identity_decision` مباشرة، وتأكد من الرفض المغلق وعدم إنشاء
   `best_match`.
3. اختبر allowlist للأدلة الموثوقة الحالية (`native_english`, `dictionary`,
   `tawreed_catalog`, وsafe audited aliases بحسب السياسة) حتى لا يتحول الحاجز
   إلى تعطيل automatic matching بالكامل.

### B. End-to-end no-promotion matrix

لكل من `review_identity` و`review_identity_prefix` و`review_fuzzy` و
`cohere_translation`:

- شغّل `ExcelTargetMatcher.match`.
- تحقق من أن `decision.best_match is None` عندما لا توجد approved manual
  decision.
- تحقق من أن المرشح، إن وُجد، موجود فقط في `review_candidates` وبـprovenance
  target/source/row key صحيح.
- تحقق من عدم استدعاء `_auto_save_excel_target_match` وعدم إنشاء
  `manual_decision=auto_matched`.
- أعد الاختبار مع `allow_live_translation=True`، مع provider mock، وتأكد من
  أن matched set لم يتغير بسبب Cohere.

### C. CLI artifact-to-UI isolation

أنشئ artifact يحتوي على option من كل نوع من الأنواع السابقة، ثم مرره عبر:

```text
_append_excel_target_review_artifacts
load_review_candidates
_load_group_candidates
_build_radio_opts
```

يجب أن تثبت assertions أن:

- `status` يبقى `no-results` و`best_match` غير موجود.
- الخيار لا يتحول إلى automatic DB row بمجرد تحميله أو عرضه.
- الاختيار البشري الصريح فقط ينشئ `approved_match`.
- `identity_evidence_kind`, `candidate_method`, `ranking_tier`, وrow provenance
  لا تضيع في round-trip.
- `review_identity`, `review_identity_prefix`, و`cached_cohere` تحمل وسمًا
  واضحًا `Review-only` في الخيار أو في provenance القريب منه، وليس fuzzy فقط.

### D. Count and display invariants

وسّع اختبار save-cap الحالي ليشمل writer ثم loader ثم UI:

- generated union أكبر من saved cap.
- saved options يساوي envelope count فعلًا.
- duplicate rows بنفس product code لكن بــsource row مختلف تبقى خيارات مستقلة.
- أي display count مسجل يحقق `C_display <= C_saved`.
- missing display count يظل `unknown/null` ولا يعامل كأنه saved أو displayed.
- أي mismatch بين summary وenvelope أو options يسبب فشل التقرير مع item key
  واضح، لا إسقاطًا صامتًا.

### E. Saved approval boundary

اختبر الحالات الأربع معًا:

1. لا توجد approval: review-only لا ينتج match.
2. legacy أو Tawreed approval: لا يفرض Excel-target match.
3. `approved_match` scoped لنفس target/file/row key: يسمح بالـmanual rebound
   المقصود فقط.
4. اختلاف file أو row أو row key أو product id: لا rebound ولا automatic
   save، وتبقى الحالة manual review.

يجب أن يثبت الاختبار أن `manual_review_rebound` استثناء ناتج عن approval موثق،
وليس evidence يمكن لمرشح جديد إنتاجه من catalog.

### F. Prefix and cross-language negative set

قبل إضافة أي قناة جديدة، ثبّت gold وnear-negative fixtures تشمل:

- exact Arabic alias.
- prefix variant مثل `فولتارين 3مبول س جديد`.
- short root.
- shared prefix لعلامة غير مرتبطة.
- manufacturer-only suffix.
- نفس brand مع form أو strength أو pack مختلف.
- unrelated brand مع score مرتفع أو numeric overlap فقط.

النتيجة المقبولة: المرشح يدخل review-only فقط، ولا ينتج automatic match، وكل
صف مسترجع يطابق catalog الحالي وrow key الحالي.

### G. Offline and mutation audit

باستخدام monkeypatch/subprocess:

- اجعل translation provider يفشل إذا استُدعي أثناء review discovery offline.
- راقب hashes لـmanual-review DB وtranslation cache وinput workbook قبل وبعد.
- اسمح فقط بكتابة artifact output المحدد.
- شغّل workers=1 وworkers=4 وتحقق من نفس automatic matched set ونفس ترتيب
  row keys/methods/tiers.

### H. Safety report gate

لا تعتمد أداة coverage قبل أن ترفض صراحة:

- `saved > generated`.
- `options != saved`.
- duplicate item record.
- option row key غير موجود أو لا يطابق catalog fingerprint الحالي.
- evidence kind غير معروف في automatic context.
- zero denominator الذي يُعاد كـprecision أو recall رقمي بدل `null`/`not measured`.

## قرار rollout

الحالة الحالية: **BLOCKED قبل cross-language expansion**.

يمكن اعتبار Gate 4 مفتوحًا فقط بعد:

1. إغلاق R1 باختبار أو allowlist fail-closed.
2. إثبات B وC لكل evidence kind، بما في ذلك Cohere مع live-provider mock.
3. إكمال round-trip وdisplay/count invariants في D.
4. إظهار review-only بوضوح في UI.
5. نجاح negative set وmutation audit وعدم تغير automatic matched set.

حتى ذلك الوقت، التحسين الحالي يعتبر نجاحًا في candidate recall للصنفين
`VOLTAREN 3AMP` و`XITHRONE 500MG 3TAB`، وليس تصريحًا بإضافة transliteration أو
cross-language discovery أوسع، ولا دليلًا على تحسن precision.
