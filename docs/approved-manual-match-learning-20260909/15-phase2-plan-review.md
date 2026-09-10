# مراجعة مستقلة لخطة المرحلة الثانية

## نطاق المراجعة

راجعت:

- الخطة [09-candidate-recall-implementation-plan.md](09-candidate-recall-implementation-plan.md).
- التحليلان المساندان [12-identity-absent-expansion-analysis.md](12-identity-absent-expansion-analysis.md)
  و[13-cross-language-candidate-recall-analysis.md](13-cross-language-candidate-recall-analysis.md).
- تنفيذ المرحلة الأولى في commit `48e8215`، مع الحالة الحالية عند `HEAD`:
  `dfa1436`.
- `excel_target_identity.py` و`excel_target_matching.py` و`excel_target_review_candidates.py`.
- مسار كتابة artifacts في `cli_order_excel_target.py` وواجهة العرض في
  `streamlit_manual_review_page.py`.
- اختبارات `candidate_recall` و`baraka_safe_matching` وتقارير التغطية.

لم أعدّل أي كود إنتاج أو إعدادات. أداة تشغيل subagent مستقلة غير متاحة في سطح
الأدوات لهذه الجولة، لذلك نفذت المراجعة الحالية بثلاثة مسارات تحليل مستقلة:
سلامة المطابقة، استدعاء المرشحين، والتشغيل/المقاييس.

## الحكم المختصر

المرحلة الأولى تعالج فئة المشكلة التي ظهرت في `VOLTAREN` و`XITHRONE` بشكل عام،
ولا تحتوي في مسارها الحالي على تسريب مباشر من `review_identity` إلى القرار
التلقائي. لكن لا أوصي بتنفيذ اقتراحات المرحلة الثانية دفعة واحدة.

الخطر الأكبر ليس أن المرشح review-only سيصبح تلقائيًا الآن، بل أن توسيع aliases
والـ fuzzy discovery والـ Arabic normalization في مسار واحد سيؤدي إلى:

1. مرشحين كثيرين غير مرتبطين بسبب تشابه prefix أو كلمات عامة.
2. دفن المرشح الصحيح خلف ترتيب غير متجانس للدرجات والحدود.
3. تحويل قرارات بشرية قديمة أو stale إلى aliases تلقائية بالخطأ.
4. صعوبة معرفة هل زادت التغطية الحقيقية أم زاد حجم القائمة فقط.

التوصية: اعتماد المرحلة الثانية كـ **review-only, bounded, measurable rollout**،
مع تنفيذ حواجز القياس والعزل قبل زيادة مصادر المرشحين.

## ما هو سليم في التنفيذ الحالي

### العزل الحالي بين review وautomatic

في `ExcelTargetMatcher.match` يتم استخدام:

```python
identified = self.identity_index.identify(item.name)
accepted, rejected = _compatible_identified(item, identified)
```

ثم تضاف نتائج `identify_review_candidates()` فقط إلى:

```python
build_review_candidates(
    ..., identified=(*identified, *review_identified), ...
)
```

هذا يعني أن `review_identity` لا يصل إلى `_compatible_identified` في المسار
الحالي. كذلك يحتفظ المرشح بمصدر Excel والملف والصف و`excel_target_row_key`.

### مصدر المرشحين مقيد بالكتالوج المحمل

`build_review_candidates` لا يقبل diagnostic إلا إذا أمكن ربطه بصف موجود في
`catalog_by_id`. وهذه حماية مهمة من تسريب مرشح Tawreed إلى قائمة Excel target.

### فصل total عن saved موجود

الـ writer يحسب `candidate_count_total` قبل تطبيق حد الحفظ، ثم يحفظ عددًا قد
يكون أقل. هذا العقد يجب الحفاظ عليه أثناء المرحلة الثانية.

## النتائج والمخاطر

### F-01 — حاجز review-only غير مثبت داخل حد المطابقة التلقائية

**الخطورة: مهمة — ليست تسريبًا قائمًا في المسار الحالي، لكنها نقطة انحدار مستقبلية.**

في `_compatible_identified` يتم رفض `cohere_translation` صراحة، لكن لا يوجد
رفض صريح لـ `review_identity` أو `review_fuzzy`. كما أن `_identity_decision`
يرفض `review_fuzzy` فقط، ولا يرفض `review_identity` صراحة:

```python
for candidate in identified:
    if candidate.evidence.kind == "cohere_translation":
        ...
    compatibility = validate_product_compatibility(...)
```

```python
if evidence.kind == "review_fuzzy":
    raise ValueError(...)
```

العزل حاليًا يعتمد على أن caller يمرر `identified` الصحيح فقط. أي refactor
مستقبلي يمرر القائمة المدمجة إلى `_compatible_identified` يمكن أن يحول مرشحًا
review-only ومتوافقًا ظاهريًا إلى auto-match.

**المطلوب قبل المرحلة الثانية:**

- جعل حد المطابقة يرفض صراحة كل evidence من نوع `review_identity` و`review_fuzzy`.
- إضافة اختبار review-only مرشح **متوافق ظاهريًا** مع بقاء `best_match is None`؛
  الاختبارات الحالية تختبر أساسًا حالة مرفوضة بسبب variant، ولا تثبت هذا
  الحاجز بأقوى صورة.
- إضافة safety assertion في evaluator تمنع أي matched row يحمل
  `review_identity` أو `review_fuzzy` دون approval صريح.

### F-02 — توسعة الـ prefix قد تنتج false positives وتضخمًا كبيرًا

التنفيذ الحالي يطابق كل صف يكون:

```python
target_brand == review_brand
or target_brand.startswith(f"{review_brand} ")
```

هذا مفيد للحالة المطلوبة، لكنه لا يثبت أن باقي الكلمات modifiers لنفس البراند.
قد تكون الصفوف مثلًا:

```text
BRAND
BRAND PLUS
BRAND PEDIATRIC
BRAND COMPANY
```

منتجات مختلفة وليست variants لنفس المنتج. الخطر هنا review false positives
وتضخم العمل، حتى لو لم يحدث auto-match.

**المطلوب:**

- اعتبار التطابق prefix إشارة `review_identity_prefix` منخفضة الثقة، وليس هوية
  كاملة.
- منع الجذور العامة أو القصيرة، ومنع الاعتماد على رقم أو شكل دوائي وحده.
- استخدام قائمة modifiers موثقة وتصنيف suffix إلى `form`, `strength`, `pack`,
  `manufacturer`, أو `brand_modifier` بدل حذفها كلها.
- قياس `candidate_count_total` وp95/p99/max على negative gold قبل وبعد.

### F-03 — درجات الأدلة الحالية غير قابلة للمقارنة وقد تدفن المرشح الصحيح

مرشح `review_identity` يحصل على score ثابت تقريبًا:

```python
score=float(identified_target.evidence.confidence) * 20.0
```

أي قرابة `18`، بينما `review_fuzzy` قد يحصل على `86` أو `90`. ثم يتم ترتيب
الجميع بترتيب score واحد في `excel_target_review_candidates.py`.

إذا زادت مصادر fuzzy في المرحلة الثانية، فقد يتجاوز المرشح الموثق بالalias
حد الحفظ أو العرض، رغم أن وجوده هو هدف الإصلاح.

**المطلوب:**

- عدم مقارنة scores من أنواع أدلة مختلفة مباشرة.
- استخدام tiers واضحة، مثل: exact identity، anchored review identity،
  variant discovery، fuzzy discovery.
- ضمان quota أو inclusion rule للمرشحين anchored قبل تطبيق cap.
- حفظ `candidate_method` أو قائمة provenance كاملة إذا ظهر الصف من أكثر من مصدر؛
  لا يكفي أن يفوز آخر مصدر بالـ `_keep_best` ويخفي أصل المرشح.

### F-04 — علم الإيقاف الحالي لا يوقف توسعة review identity

الإعداد الحالي يحتوي:

```yaml
excel_target_review_candidates_enabled: true
```

لكن `match()` يمرر هذا الإعداد إلى `review_discovery` فقط، ثم يستدعي
`identify_review_candidates()` دائمًا. لذلك إيقاف discovery لا يوقف بالضرورة
مرشحي `review_identity` الجدد.

قد يكون هذا مقصودًا إذا كان الإعداد خاصًا بـ fuzzy discovery، لكنه غير واضح
تشغيليًا، وسيصبح مشكلة عندما توجد rollout أو rollback للمرحلة الثانية.

**المطلوب:**

- تعريف واضح: هل العلم يوقف كل review candidates أم fuzzy discovery فقط؟
- إذا كان مطلوبًا كـ kill switch للمرحلة الثانية، يجب أن يغطي review identity
  أيضًا، مع اختبار disabled/enabled.
- لا تعتمد على تغيير config فقط دون التحقق من artifact الناتج.

### F-05 — إدخال `identity_absent` إلى manual review يحتاج بوابة أقوى من fuzzy score

الاقتراح مفيد للتغطية، لكنه أخطر اقتراح من ناحية false positives. كما يوضح
التحليل 12، فإن `identity_absent` الذي لديه discovery موثوق يدخل manual review
بالفعل في المسار الحالي؛ لذا لا نحتاج تغيير هذا الشرط العام. التغيير الحقيقي
المحتمل هو توسيع discovery ليولد مرشحين أكثر. إذا أصبح كل identity-absent ذي
تشابه محدود manual-review، فستدخل أصناف كثيرة بسبب:

- كلمة عامة مشتركة.
- رقم أو form مشترك.
- typo قريب من اسم دواء آخر.
- مرشح English قريب بينما الصف العربي لا يملك هوية ثنائية موثقة.

**التوصية:** لا نفتح هذا المسار لكل `identity_absent` مباشرة. نحافظ على السلوك
الحالي discovery-only، ونختبره صراحة، ثم يبدأ أي توسع جديد كمسار
`discovery_only` مستقل، ولا يحتفظ بمرشح إلا عند تحقق مجموعة شروط:

1. token براند meaningful، وليس رقمًا أو form فقط.
2. حد score أدنى وحد margin أو ambiguity معلوم.
3. provenance كامل إلى target/catalog row.
4. حد أعلى per-item وper-run.
5. عدم وجود conflict صريح في البراند أو manufacturer.
6. وجود negative gold قريب لا يتحول إلى candidate بلا سبب.

يجب أن تكون الزيادة في manual-review coverage metric منفصلة عن precision؛
رفع عدد الحالات وحده ليس نجاحًا.

### F-06 — Arabic index مستقل مفيد، لكن reverse mapping العام خطر

إنشاء فهرس عربي مستقل هو الاقتراح الأعلى قيمة بعد القياس، لأن ملفات Excel قد تكون
عربية بالكامل. لكن ربط كل اسم عربي بكل alias إنجليزي أو استخدام fuzzy cross-language
على كامل الكتالوج سيكسر boundary الحالية التي تمنع خلط اللغتين.

**التنفيذ الآمن المقترح:**

- ابدأ بـ exact audited bilingual alias.
- وسّع إلى review-normalized Arabic variants داخل نفس target فقط.
- سجّل الدليل كـ `review_identity` أو `review_identity_prefix`.
- لا تستخدمه في `identify()` أو `_identity_decision` قبل دورة مستقلة من gold
  cases وnegative cases وموافقة بشرية.

### F-07 — توسيع التطبيع العربي يحتاج negative tests لا قائمة كلمات أطول فقط

الـ review normalizer الحالي يزيل كلمات كثيرة مثل form/status، ويعالج `س` فقط
عندما يجد decoration. هذا ينجح في الأمثلة الحالية، لكن يمكن أن يزيل suffix
حقيقيًا أو يجعل alias قصيرًا يساوي عدة أسماء.

قبل إضافة patterns جديدة يجب إنشاء matrix تشمل:

```text
bare brand
brand + meaningful suffix
brand + form
brand + strength + pack
brand + manufacturer
brand with Arabic digits
same text with one-character status
unrelated brand sharing the first token
```

كل pattern جديد يحتاج positive وnegative وnear-negative، ويجب أن يبقى
`normalize_arabic_brand` التلقائي غير متغير أثناء تطوير review-only.

### F-08 — `candidate_count_total` لا يعني كل الصفوف الممكنة

الـ total الحالي هو عدد المرشحين الذي أنتجته المسارات الحالية. لكنه يتأثر بـ:

- `excel_target_review_candidate_limit` لمسار discovery.
- `manual_review_save_candidate_limit` للـ artifact.
- `manual_review_display_candidate_limit` للواجهة.
- dedup وترتيب `_keep_best`.

لذلك لا يجوز تسمية `candidate_count_total` “كل المرشحين الممكنين” بعد إضافة
مصادر جديدة دون تعريف universe واضح.

**يجب فصل المقاييس إلى:**

```text
C_identity       = rows from exact/anchored identity
C_discovery      = rows from fuzzy/discovery
C_union          = deduplicated bounded review universe
C_saved          = rows persisted in JSONL/CSV
C_display        = rows currently shown in UI
```

والـ gold recall يجب أن يُقاس على `row_key` داخل `C_union` ثم داخل `C_saved`، لا
على عدد الحالات التي أصبحت manual review فقط.

## تقييم اقتراحات المرحلة الثانية

| الاقتراح | القرار | الترتيب | القيد الأساسي |
|---|---|---:|---|
| إدخال `identity_absent` ذات discovery إلى المراجعة | السلوك موجود؛ أضف regression ثم وسّع discovery بحذر | 5 | discovery-only، meaningful token، score+margin، negative gold، budgets |
| زيادة aliases من Tawreed/dictionary/cache | موافقة مشروطة | 3 | مصدر موثق، target-scoped، لا تفعيل تلقائي مباشر |
| Arabic index مستقل | موافقة عالية الأولوية | 2 | يبدأ من audited bilingual anchor ولا يعمل cross-language fuzzy عامًا |
| توسيع Arabic normalization | موافقة تدريجية | 4 | pattern registry واختبارات negative/near-negative |
| تقسيم المرشحين إلى buckets | موافقة عالية الأولوية | 1 | tiers وquota تمنع دفن anchored candidate ولا تلغي cap |
| تحسين ranking مع الحفاظ على التنوع | موافقة عالية الأولوية | 1 | لا تخلط درجات الأدلة؛ ترتيب deterministic وrow-key tie-break |
| pagination وزيادة العرض في UI | موافقة بعد تثبيت artifacts | 6 | `C_saved` يجب أن يغطي `C_display`، مع provenance وtotal واضح |
| التعلم من القرارات اليدوية | آخر مرحلة | 7 | proposal queue فقط؛ لا alias تلقائي من approval قديم أو stale |
| قياس coverage/recall/precision | شرط سابق لكل ما سبق | 0 | gold، negative gold، fingerprints، determinism، safety gates |

## ترتيب التنفيذ الموصى به

### المرحلة 2-0: تثبيت الحواجز والقياس

- اختبار صريح يمنع `review_identity` و`review_fuzzy` من automatic matching.
- إضافة `match_origin` وevidence type كحقول مستقلة في evaluator.
- تثبيت gold positives للحالتين الحاليتين، وnegative rows قريبة منهما.
- إنشاء manifest للـ config/catalog/input/cache/DB fingerprint.
- قياس `C_identity`, `C_discovery`, `C_union`, `C_saved`, `C_display` قبل أي
  تغيير threshold.

### المرحلة 2-1: ترتيب bounded ومتعدد المصادر

- فصل candidate tiers بدل score واحد.
- ضمان ظهور anchored rows ضمن save budget.
- dedup على `excel_target_row_key` مع الاحتفاظ بكل provenance methods.
- اختبار tie-break وثبات الترتيب مع نفس catalog ومع `item-workers 1` و`4`.

### المرحلة 2-2: توسيع Arabic review index

- aliases موثقة فقط.
- Arabic variants داخل target نفسه.
- negative tests للـ prefix والجذور العامة والـ manufacturer modifiers.
- قياس tail size ووقت بناء الفهرس والذاكرة.

### المرحلة 2-3: توسيع discovery لـ identity-absent

- feature gate مستقل.
- لا يُفتح إلا على مجموعة shadow/replay أولًا.
- الاحتفاظ بالمصدر `discovery_only` وعدم إدخاله في automatic identity.
- إيقاف rollout إذا زاد false-positive sample أو p99 candidate count عن الحد.

### المرحلة 2-4: واجهة العرض والحفظ

- التأكد أن كل `C_saved` قابل للوصول، وليس فقط أول خمسة.
- إبقاء pagination الحالية للعناصر، وإضافة pagination/تحميل واضح للمرشحين إذا
  احتاجت القائمة لذلك.
- عرض target/file/row key/method/review status/compatibility reason.

### المرحلة 2-5: حلقة التعلم البشرية

لا تبدأ إلا بعد نجاح المراحل السابقة. القرار اليدوي يتحول إلى proposal فقط إذا:

- `manual_decision == approved_match`.
- `matching_source == excel-target`.
- target key وrow key حاليان ومطابقان للكتالوج الحالي.
- لا توجد stale أو scope mismatch.
- يوجد positive case ومعه أقرب negative cases.
- تمت مراجعة بشرية ثانية أو adjudication للحالات المؤثرة.

بعد ذلك يفعّل alias في review-only أولًا، ثم يُعاد shadow evaluation. لا ينتقل
إلى automatic matching إلا عبر خطة مستقلة وموافقة صريحة.

## بوابات قبول المرحلة الثانية

لا تعتبر المرحلة ناجحة إلا إذا تحققت كلها:

- `recall_union` للحالات الذهبية لا ينخفض.
- `recall_saved` للحالات الذهبية لا ينخفض تحت نفس save budget.
- لا يوجد auto-match من `review_identity` أو `review_fuzzy` أو
  `discovery_only`.
- لا يوجد option من Tawreed أو target آخر.
- كل row key فريد وثابت، والترتيب ثابت عند إعادة التشغيل.
- `saved <= union` و`display <= saved` عند تطبيق الحدود المعلنة.
- candidate count p95/p99/max داخل budget معلن، أو يوجد تفسير وموافقة للتجاوز.
- لا تتغير نتائج المطابقة التلقائية الحالية دون evidence مستقل.
- replay offline لا يغيّر قواعد البيانات.
- كل زيادة في manual-review coverage مصحوبة بعينة precision يراجعها إنسان.

## قرار المراجعة

**التوصية النهائية: CONDITIONAL GO.**

يمكن البناء على المرحلة الأولى، لكن الأولوية ليست خفض thresholds أو إضافة aliases
بأكبر عدد. الأولوية هي تثبيت حاجز automatic، تعريف universe، ثم ranking/budget
متعدد المصادر. بعد ذلك يكون Arabic anchored expansion هو التوسعة الأولى، ثم
identity-absent discovery، ثم حلقة التعلم البشرية.

بهذا نزيد احتمال ظهور المرشح الصحيح دون تحويل manual review إلى قائمة ضوضاء أو
تسريب evidence غير موثوق إلى المطابقة التلقائية.
