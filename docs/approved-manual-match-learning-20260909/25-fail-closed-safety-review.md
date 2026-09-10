# مراجعة أمان مسار fail-closed

التاريخ: 2026-09-10

## نطاق المراجعة

راجعت فقط التغييرات الحالية المتعلقة بـ:

- `_AUTOMATIC_IDENTITY_KINDS` وحاجز `_compatible_identified` و`_identity_decision`.
- رفض `unknown` و`discovery_only` تلقائيًا.
- اختبارات `tests/core/excel_target/test_excel_target_candidate_recall.py`.
- حفظ وعرض provenance في Streamlit، خصوصًا `excel_target_row_key`.
- احتمال حدوث regression في evidence kinds المسموح بها أو `manual_review_rebound`.

لم أعدّل كودًا أو `state` أو ملفات الإدخال.

## الحكم المختصر

الحاجز الحالي **fail-closed بشكل صحيح داخل مسار الهوية**: النوع غير الموجود في
الـallowlist لا يستطيع الوصول إلى `_identity_decision`، و`cohere_translation`
والأنواع review-only المعروفة ما زالت مرفوضة صراحة. لا يوجد في diff الحالي دليل
على أن `unknown` أو `discovery_only` يمكن أن ينتجا `best_match` عبر مسار الهوية.

إضافة `manual_review_rebound` إلى الـallowlist ليست regression في المسار الحالي؛
هي استثناء مقصود لموافقة بشرية محفوظة ومقيدة بالمصدر والهدف والصف. لكنها تحتاج
إلى إبقاء هذا النوع مرتبطًا بذلك المسار وعدم استخدامه كـidentity evidence عام.

المراجعة لا تعتبر الحماية مكتملة end-to-end بعد، بسبب فجوات اختبار وعرض UI
موضحة أدناه.

## النتائج

### 1. PASS — allowlist يمنع الأنواع غير المعروفة

في `src/core/excel_target/excel_target_matching.py:48-57` الأنواع المسموح بها
تلقائيًا هي فقط:

```text
native_english
dictionary
cached_translation
safe_alias
tawreed_catalog
manual_review_rebound
```

وفي `:205-217` يحدث الرفض بالترتيب التالي:

1. رفض `cohere_translation` وفق سياسة الأمان الحالية.
2. رفض `review_identity` و`review_identity_prefix` و`review_fuzzy`.
3. رفض أي نوع غير موجود في `_AUTOMATIC_IDENTITY_KINDS`.

كما يوجد حاجز ثانٍ في `_identity_decision` عند `:422-427`، لذلك لا يكفي أن
يتجاوز نوع ما فحص التوافق؛ يجب أن يكون allowlisted أيضًا قبل إنشاء `best_match`.

هذه نقطة جيدة أمنيًا لأن إضافة evidence kind جديد مستقبلًا ستفشل مغلقًا إلى أن
يُراجع ويُضاف صراحة إلى allowlist.

### 2. PASS مع ملاحظة — `unknown` و`discovery_only`

الاختبار الجديد في
`tests/core/excel_target/test_excel_target_candidate_recall.py:53-70`
يختبر النوعين `unknown_future` و`discovery_only`، ويتحقق من نتيجتين صحيحتين:

- `_compatible_identified` يعيد candidate فارغًا وسببًا يطلب manual review.
- `_identity_decision` يرفع `ValueError` بدل إنتاج قرار تلقائي.

هذا يثبت الحاجزين المباشرين. لكنه لا يثبت كامل السلسلة من
`ExcelTargetMatcher.match()` إلى JSONL ثم Streamlit؛ لا يوجد في هذا الاختبار
حقن evidence مجهول داخل matcher ولا assertion على `decision.best_match` في
مسار تشغيل كامل.

### 3. MEDIUM — فجوة اختبار end-to-end وليست تسريبًا مثبتًا

الاختبار الحالي يستدعي دوالًا داخلية مباشرة. لذلك قد يمر رغم وجود regression
في أحد الآتي:

- مسار آخر يستدعي `_identity_decision` أو يبني `MatchDecision` مباشرة.
- writer يحوّل `discovery_only` إلى candidate artifact ثم loader يعيد تصنيفه.
- UI يعرض candidate review-only كأنه auto-match.

التوصية في التقرير فقط: إضافة اختبار تكاملي يثبت أن evidence مجهول أو
`discovery_only` لا يصل إلى `decision.best_match`، ثم اختبار round-trip للـartifact
يثبت بقاء evidence kind و`review-only` status.

### 4. PASS جزئي — provenance يحافظ على الصف الفيزيائي

التغييران في Streamlit يعملان في الاتجاه الصحيح:

- `_load_group_candidates` يستخدم `excel_target_row_key` ضمن identity عند الدمج
  في `src/ui/manual_review/streamlit_manual_review_page.py:244-269`.
- `_render_candidate_provenance` يستخدم الصف نفسه ضمن scope عند `:433-472`.

وبالتالي لا يتم دمج صفين من نفس المنتج أو نفس الملف إذا كان لكل منهما row key
مختلف. الاختبار `test_candidate_provenance_keeps_distinct_physical_rows` يثبت
أن captionين يتم إنتاجهما للصفين `row-a` و`row-b`.

لكن الاختبار لا يفحص نص الـcaption نفسه؛ لذلك لا يثبت صراحة أن row key ظهر في
النص، ولا أن evidence detail/status الصحيحين ظهرا. كذلك provenance المعروض هو
لـ`visible_options` فقط بعد تطبيق حد العرض في `:240-241`، وليس بالضرورة لكل
candidate محفوظ في artifact.

### 5. MEDIUM — تنبيه review-only في UI غير موحد

في `src/ui/manual_review/streamlit_manual_review_page.py:454-457` يظهر
تنبيه صريح `Review-only` فقط عندما يكون `identity_evidence_kind ==
"review_fuzzy"`. وفي `:674` يتكرر نفس الشرط داخل label الخاص بالاختيار.

لذلك `review_identity` و`review_identity_prefix`، وكذلك أي
`discovery_only` أو evidence مجهول محفوظ مستقبلًا، ستظهر مع evidence kind في
provenance لكن دون نفس العبارة الصريحة التي تؤكد أن الموافقة البشرية مطلوبة.
هذا لا يسمح بالـautomatic match، لكنه regression محتمل في وضوح القرار البشري:
قد يفسر المستخدم candidate review-only على أنه verified candidate.

### 6. `manual_review_rebound` — مسموح عمدًا مع حد ثقة واضح

إدراج `manual_review_rebound` في allowlist صحيح للمسار الحالي لأن مصدره
`_scoped_manual_review` فقط، وهو يُنفّذ قبل matching العادي، ويتحقق من:

- `matching_source == "excel-target"` وtarget key المطابق.
- row key المطابق إذا كانت الموافقة scoped.
- تطابق المنتج الحالي أو وجود candidate متوافق وحيد في المسار القديم.
- تسجيل `DecisionSource.MANUAL_REVIEW_SAVED` بعد rebound.

لذلك لا أعتبره regression حاليًا؛ فهو تحويل لموافقة بشرية سابقة إلى match
مقصود، وليس اكتشاف هوية جديدًا.

الخطر المستقبلي هو أن يستدعي caller آخر `_compatible_identified` أو
`_identity_decision` مع `IdentityEvidence("manual_review_rebound", ...)` مصطنعًا؛
الـallowlist وحده لا يثبت أن الدليل جاء فعلًا من `ManualReviewStore`. لا يوجد
هذا الاستخدام في call sites الحالية التي راجعتها، لكنه يستحق اختبارًا أوضح
يحصر هذا النوع في مسار rebound.

### 7. evidence kinds المسموح بها — لا regression حالي مثبت

- `native_english`, `dictionary`, `cached_translation`, `safe_alias` و
  `tawreed_catalog` هي الأنواع التي ينشئها index الحالي وتظل مسموحة.
- `cohere_translation` موجود في identity index لكنه مرفوض صراحة قبل allowlist؛
  هذا متوافق مع safe policy.
- `manual_review` موجود في `IdentityKind` كنوع، لكنه غير موجود في allowlist ولا
  يوجد producer حالي له في المسار الذي راجعته؛ لذلك سيُرفض، وهو السلوك الآمن.
- `discovery_only` ليس جزءًا من `IdentityKind` type literal حاليًا، لكن اختبار
  runtime يثبت أن قيمة string غير المعروفة تُرفض. عند إضافة هذا النوع رسميًا
  يجب أن يبقى خارج allowlist وأن يبقى review-only.

## الاختبارات والتحقق

نجح الاختبار المحدد:

```text
tests/core/excel_target/test_excel_target_candidate_recall.py
tests/ui/manual_review/test_streamlit_manual_review.py
37 passed in 1.60s
```

محاولة تشغيل اختبارات rebound المحددة لم تكتمل بسبب `NameError` مستقل حول
`_build_review_aliases` في مسار اختبار `test_baraka_safe_matching.py`. لا أنسب
هذا الفشل إلى تغييرات allowlist أو Streamlit، لكنه يعني أن سلوك
`manual_review_rebound` لم يُعاد التحقق منه بهذا الأمر الأخير.

## القرار النهائي

- **Fail-closed للهوية:** PASS.
- **رفض unknown/discovery_only في الدوال المحمية:** PASS.
- **حفظ row-level provenance في الدمج والعرض:** PASS جزئيًا.
- **سلامة `manual_review_rebound`:** لا regression حالي؛ استثناء مقصود مع خطر
  مستقبلي إذا استُخدم النوع خارج مسار الموافقة المحفوظة.
- **جاهزية الإغلاق الكامل:** تحتاج اختبار end-to-end موحد وتنبيه UI صريح لكل
  review-only evidence kind قبل اعتبار الحماية مكتملة عبر كامل pipeline.
