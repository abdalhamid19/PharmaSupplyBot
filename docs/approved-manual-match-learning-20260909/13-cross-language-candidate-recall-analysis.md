# Cross-language candidate recall analysis

## النطاق والنتيجة المختصرة

هذا التقرير يحلل المرحلة التالية من تحسين `candidate recall` في Excel targets
دون تعديل كود الإنتاج. التركيز على `ExcelTargetReviewDiscoveryIndex`، وعلى
الفجوة الناتجة عن اختيار projection أحادية اللغة، وعلى تصميم بحث عربي/إنجليزي
يدعم aliases وtransliteration في مسار المراجعة اليدوية فقط.

النتيجة الأساسية:

> الفهرس الحالي يحافظ عمدًا على الفصل بين العربية والإنجليزية، لكنه لا يملك
> seam للبحث cross-language. لذلك فإن طلبًا إنجليزيًا مثل
> `VOLTAREN 3AMP` لا يصل إلى صف Excel عربي لا يملك `trusted_name_en` إلا إذا
> وُجدت هوية ثنائية اللغة exact في مسار آخر.

الإصلاح السابق عالج جزءًا محددًا من هذه الفجوة: alias ثنائي اللغة موثق يوسّع
صفوف البراند العربية للـ manual review. المرحلة التالية ينبغي أن تجعل هذا
التوسع عامًا ومتعدد القنوات، مع بقاء قرار المطابقة التلقائية معزولًا بالكامل.

## حدود هذا التحليل

- تم فحص source code والاختبارات والوثائق المحلية باعتبارها المصادر الأولية.
- لا يتضمن التقرير تعديلًا في `src/` أو `tests/` أو `state/`.
- الاقتراحات هنا تصميمية؛ لا ينبغي تنفيذ transliteration أو توسيع discovery
  قبل إضافة gold labels وnegative cases وقياس replay.

## خريطة الملفات الحالية

| الملف | الدور الحالي | الملاحظة التي تؤثر على recall |
|---|---|---|
| [`excel_target_review_discovery.py`](../../src/core/excel_target/excel_target_review_discovery.py) | يبني `_english_entries` و`_arabic_entries` ويعمل fuzzy discovery | `build` يضيف English rows فقط عند وجود `trusted_name_en`؛ `discover` يختار projection واحدة من `_query_projection` حسب وجود حروف عربية في الطلب. راجع السطور 89–196. |
| [`excel_target_identity.py`](../../src/core/excel_target/excel_target_identity.py) | يبني الهوية الثنائية وaliases ويعيد `IdentifiedTarget` | `identify` هو مسار الهوية المستخدم قبل القرار التلقائي. `identify_review_candidates` مسار review-only منفصل منذ الإصلاح السابق. راجع السطور 91–303. |
| [`excel_target_matching.py`](../../src/core/excel_target/excel_target_matching.py) | ينسق decision وdiscovery وبناء المرشحين | `_compatible_identified` يستقبل نتائج `identify` فقط؛ نتائج discovery و`review_identified` تذهب إلى `build_review_candidates` بعد انتهاء مسار القرار. راجع السطور 89–130. |
| [`excel_target_review_candidates.py`](../../src/core/excel_target/excel_target_review_candidates.py) | يحول evidence إلى مرشحين قابلين للحفظ | يقبل `discovery_hits` و`identified` وdiagnostics، يتحقق من أن الصف موجود في catalog الحالي، ثم يزيل التكرار باستخدام row key. راجع السطور 165–273. |
| [`excel_target_aliases.py`](../../src/core/excel_target/excel_target_aliases.py) | يحل aliases الإنجليزية المحافظة | لا يفهرس alias إلا إذا كان الجانب العربي يطابق صفًا في catalog؛ resolver نفسه يعيد evidence محافظًا ويترك variant compatibility للطبقة الأعلى. راجع السطور 190–316. |
| [`excel_target_loader.py`](../../src/core/excel_target/excel_target_loader.py) | يحول صفوف Excel إلى `TargetProduct` | `name_ar`, `source_file`, `source_row_number`, و`store_product_id` تحمل provenance المطلوب لعزل مصدر Excel. |
| [`cli_order_excel_target.py`](../../src/cli/commands/cli_order_excel_target.py) | يكتب summary وmanual-review artifacts | يحسب `candidate_count_total` قبل حد الحفظ، ثم يكتب `options` التي تحمل مصدر الصف ورقم الصف وrow key. راجع السطور 278–346 و587–673. |
| [`bilingual_brand_matcher.py`](../../src/core/normalization/bilingual_brand_matcher.py) | matcher ثنائي اللغة أقدم/عام | يضم dictionary وtranslation cache/live scoring. الوصف يذكر transliteration، لكن لا يوجد في implementation الحالي استدعاء فعلي لـ `pyarabic` أو index transliterated داخل `ExcelTargetReviewDiscoveryIndex`. يجب عدم استيراد هذا المسار إلى automatic matching بلا عقد سلامة واضح. |
| [`translation.py`](../../src/core/normalization/translation.py) | cache وbatch/live translation | `ar_to_en_many` قد يستدعي Cohere عند غياب cache، لذلك لا ينبغي أن يستعمله discovery التفاعلي بشكل ضمني. راجع السطور 568–629. |
| [`test_excel_target_review_discovery.py`](../../tests/core/excel_target/test_excel_target_review_discovery.py) | اختبارات discovery | تغطي same-language English وsame-language Arabic والـ ambiguity والـ attribute conflicts، ولا تغطي English query مع Arabic-only catalog عبر alias/transliteration. |
| [`test_excel_target_candidate_recall.py`](../../tests/core/excel_target/test_excel_target_candidate_recall.py) | regression لحالة البركة وreview identity | يثبت أن المرشح الصحيح يدخل review candidates ولا يصبح automatic match. يجب توسيعه لاختبارات cross-language العامة وليس أسماء الحالات فقط. |
| [`06-candidate-recall-code-map.md`](06-candidate-recall-code-map.md) | تحليل المسار السابق | يوثق أن فقد المرشح يحدث upstream قبل writer، وأن حد الحفظ لا يعيد مرشحًا لم يدخل أصلًا إلى evidence set. |
| [`09-candidate-recall-implementation-plan.md`](09-candidate-recall-implementation-plan.md) | خطة الإصلاح السابق | يحدد seam منفصلًا بين exact identity وreview-only identity؛ ينبغي أن تبقى هذه القاعدة أساس المرحلة الجديدة. |

## السلوك الحالي بالتفصيل

### 1. الفهرس أحادي اللغة

`ExcelTargetReviewDiscoveryIndex.build` يبني projections مستقلة:

```text
trusted_name_en موجود  -> _english_entries
name_ar عربي           -> _arabic_entries
```

ثم يقرر `_query_projection`:

```text
وجود حرف عربي في الطلب -> arabic_fuzzy
غير ذلك                -> english_fuzzy
```

بعد ذلك يتم حساب `fuzz.ratio` داخل projection المختارة فقط، مع اشتراط shared
meaningful brand token، ثم تصنيف strong/medium/ambiguous وتطبيق `limit`.

هذا التصميم يحمي من مقارنة نص عربي كنص إنجليزي، لكنه ينتج فجوة recall واضحة:

```text
order:  VOLTAREN 3AMP       -> english_fuzzy
Excel:  فولتارين 3مبول س جديد -> لا trusted_name_en
النتيجة: لا cross-language discovery
```

وجود الترجمة أو dictionary في modules أخرى لا يغير هذا السلوك تلقائيًا؛ لا يوجد
adapter يضيف تلك النتائج إلى `_english_entries` أو يعيدها إلى `ReviewDiscoveryHit`.

### 2. الهوية والقرار التلقائي منفصلان عن discovery

المسار الحالي في matcher هو:

```text
saved approval (إن وجد)
  -> identity_index.identify
  -> compatibility
  -> automatic/native decision
  -> review discovery
  -> build_review_candidates
```

النتيجة المهمة للمرحلة القادمة: توسيع discovery أو aliases لا يجب أن يغير
`identify` المستخدم في `_compatible_identified`. أي candidate ناتج من
cross-language fuzzy أو transliteration أو cached translation يجب أن يحمل
`review-only` evidence ولا يدخل automatic acceptance.

### 3. عزل صف Excel موجود بالفعل

`build_review_candidates` لا يكتفي بمعرف المنتج العام؛ فهو يربط كل candidate
بـ target catalog الحالي ويستعمل row-aware key يتضمن target/source/row/code/name.
هذا مهم لأن catalog قد يحتوي نفس code في أكثر من صف أو variant.

أي design جديد يجب أن يحافظ على invariant الآتي:

```text
cross-language evidence يحدد صفًا من catalog الحالي فقط
ولا ينشئ candidate من Tawreed أو dictionary أو translation row
```

ويجب أن يبقى payload النهائي `source_kind=excel-target` مع:

- `target_key`.
- `source_file`.
- `source_row_number`.
- `excel_target_row_key`.
- evidence channel وscore وmargin وسبب compatibility.

## التصميم العام المقترح

### المبدأ: عدة قنوات recall داخل review plane واحد

بدل إضافة شرط خاص بكل براند، يصبح `ExcelTargetReviewDiscoveryIndex` أو adapter
داخلي له فهرس متعدد الإسقاطات. واجهته الخارجية تظل صغيرة:

```python
discover(item, config) -> tuple[ReviewDiscoveryHit, ...]
```

أما implementation فيحتوي projections متعددة ويجمعها قبل الترتيب:

1. `native_english`: صف Excel الذي يملك اسمًا إنجليزيًا موثوقًا.
2. `native_arabic`: الاسم العربي بعد التطبيع العربي الحالي.
3. `audited_bilingual_alias`: alias EN↔AR من Tawreed أو dictionary، مربوط
   بالـ target catalog الحالي.
4. `cached_translation`: ترجمة مخزنة مسبقًا فقط، مع model/source metadata.
5. `arabic_transliteration`: تمثيل Latin مشتق من الاسم العربي أو brand stem.
6. `same_script_fuzzy`: fuzzy داخل نفس اللغة فقط.

كل قناة تعيد evidence row لا decision. الدمج النهائي يتم بالـ row key، مع
الاحتفاظ بأفضل evidence ويفضل أيضًا الاحتفاظ بقائمة القنوات التي دعمت الصف.

### واجهة evidence المقترحة

يجب أن تكون هوية الدليل صريحة ومفيدة للمراجع والقياس، مثل:

```text
channel: audited_bilingual_alias | cached_translation | transliteration | same_script_fuzzy
mode: review-only
query_projection: english | arabic | mixed
canonical_query: ...
canonical_candidate: ...
score: ...
runner_up_score: ...
margin: ...
source: tawreed | dictionary | translation_cache | deterministic_transliteration
compatibility_status: compatible | rejected | unknown
```

لا ينبغي تسمية transliteration أو translation باسم `safe_alias`؛ ذلك يمنع خلط
evidence استكشافي مع alias تم اعتماده للمطابقة التلقائية.

### مسار البحث المقترح

```text
1. parse query and detect scripts
2. create normalized English, Arabic, and optional transliterated brand keys
3. collect exact audited bilingual aliases
4. collect target-scoped review expansion for those aliases
5. collect cached-translation and transliteration hits
6. collect same-script fuzzy hits
7. validate every row against the loaded Excel catalog
8. deduplicate by target-aware row key
9. rank with channel priority + score + compatibility + diversity
10. return review candidates only
```

الترتيب يجب أن يفضل evidence الأكثر قابلية للتدقيق، لا مجرد أعلى score قابل
للمقارنة بين قنوات مختلفة:

```text
audited alias > exact cached translation > exact transliteration
> same-script strong fuzzy > same-script medium fuzzy
```

هذه priority ليست automatic confidence؛ هي فقط ترتيب عرض للمراجع.

## تصميم البحث العربي/الإنجليزي

### Query parsing

ينبغي ألا يختار النظام لغة واحدة من خلال أول فحص boolean فقط. الأفضل إنتاج
`QueryViews` متعددة من نفس الاسم:

- `raw_name` كما وصل من order.
- `english_brand_view` بعد إزالة form/strength/pack المعروفة.
- `arabic_brand_view` إذا كان الاسم مختلطًا أو يحتوي alias عربي.
- `transliteration_brand_view` للعناصر العربية فقط أو الجزء العربي.
- `attribute_view` منفصل يحتوي strength/form/pack/concentration.

الـ attribute view لا يختفي أثناء البحث؛ يتم استعماله للترتيب والشرح، لا
لاستنتاج brand من كلمات عامة مثل `30 TAB` أو `3 قرص`.

### Arabic projection

يظل `normalize_arabic_brand` الحالي هو التطبيع الآمن لمسار automatic identity.
للمراجعة يمكن وجود view أوسع، كما حدث في الإصلاح السابق، لكن يجب أن يكون:

- منفصل الاسم عن `normalize_arabic_brand`.
- موثقًا بأن استخدامه recall-only.
- محافظًا على حالات negative مثل brand ينتهي فعلًا بـ `س`.
- لا يحذف كلمة إلا إذا كانت decoration أو status موثقة في سياقها.
- يدعم الأرقام العربية/الإنجليزية والمسافات والشرطات دون إزالة tokens
  meaningful عشوائيًا.

### English projection

يجب الاحتفاظ بـ `normalize_english_brand` كـ identity key الحالي، وإضافة
`EnglishReviewView` فقط إذا كانت الحاجة إلى إزالة variants أوسع. لا ينبغي أن
تتحول إزالة modifier مثل `PLUS`, `XR`, `FORTE`, أو digit-bearing brand إلى
قاعدة عامة؛ هذه tokens قد تكون جزءًا حقيقيًا من البراند.

### Mixed-script queries

أسماء مثل `HERO بيبي LF` أو `BRAND 3قرص` يجب ألا تقع في projection واحدة
بشكل عشوائي. الاقتراح:

- استخراج contiguous script spans.
- تطبيع كل span بلغته.
- إنشاء aliases من كل span فقط إذا كان هناك evidence bilingual موثق.
- إبقاء query كاملًا للـ compatibility.
- عدم استخدام shared generic token كـ anchor وحيد.

## تصميم aliases وtransliteration review-only

### طبقة alias graph موجهة بالـ target

الـ alias relation الأفضل أن تكون record قابلة للتدقيق وليست قاموسًا عالميًا:

```text
AliasEvidence(
    query_form,
    arabic_form,
    target_key,
    source_kind,
    source_record,
    confidence,
    review_only=True,
)
```

قواعد الفهرسة:

1. لا يُفهرس alias إلا إذا كان الجانب العربي أو canonical target مربوطًا بصف
   حقيقي في نفس catalog.
2. إذا ربط alias أكثر من brand غير متوافق، يبقى ambiguity ولا يصنع automatic
   match.
3. إذا ربط أكثر من row variant لنفس البراند، تعرض rows كلها وفق limit/diversity
   مع أسباب اختلاف العبوة أو القوة.
4. أي alias ناتج عن manual decision يدخل queue للاعتماد، ولا يصبح global alias
   في نفس اللحظة.
5. يجب حفظ source (`tawreed`, `dictionary`, `manual-approved`, `cache`) حتى
   يمكن إيقاف قناة واحدة دون حذف بقية المرشحين.

### الترجمة المخزنة

الـ cached translation مفيدة كقناة review-only، بشرط:

- لا live network call أثناء `discover` لكل item.
- حفظ model/version ووقت cache إن أمكن.
- اعتبار الترجمة candidate evidence لا identity proof.
- عدم استعمال ترجمة منخفضة الجودة كـ alias دائم.
- تطبيق score/margin وnegative labels قبل عرضها.

الـ pre-translation batch يمكن أن يجهز view منفصلة، لكن يجب ألا يجعل
`ExcelTargetReviewDiscoveryIndex` يعتمد على provider state أو latency أثناء
المطابقة التفاعلية.

### Transliteration

التصميم الآمن هو Arabic → Latin للجزء العربي من catalog/query، وليس محاولة
استنتاج Arabic من أي English spelling. transliteration ينبغي أن يكون channel
مساعدًا لا canonical identity، لأن:

- أكثر من Arabic spelling قد ينتج نفس Latin string.
- الأسماء التجارية قد تكون transliteration صوتية غير حرفية.
- الأسماء ذات أصل غير عربي لا يمكن استعادتها reliably من transliteration.
- word order وspaces و`ح/خ/ق` قد تصنع collisions.

التنفيذ المقترح عند مرحلة لاحقة:

1. normalize Arabic diacritics/tatweel/digits أولًا.
2. استخرج brand stem قبل transliteration، ولا تخلط `30 قرص` في المقارنة.
3. أنشئ تمثيلًا Latin واحدًا deterministic أو عددًا صغيرًا من variants
   المسموح بها، مع تسجيل scheme/version.
4. index by transliterated brand stem مع token boundary وminimum meaningful
   length.
5. لا تعرض transliteration candidate إلا إذا كان هناك anchor كافٍ وmargin
   ضد runner-up.
6. لا تمرر هذه النتيجة إلى `identify` أو `_compatible_identified`.

يوجد بحث سابق في `docs/research/research_arabic_english_drug_matching.md`
عن pyarabic وقيود transliteration. يجب اعتباره design input، لا دليلًا على أن
المسار مطبق حاليًا في `ExcelTargetReviewDiscoveryIndex`.

## الحفاظ على عزل مصدر Excel

cross-language recall لا يبرر خلط المصادر. يجب فرض هذه invariants في التصميم:

### Catalog boundary

الفهرس يُبنى لكل `target_key` ولكل مجموعة صفوف Excel محملة لذلك الهدف. لا يوجد
global index يعيد صفًا من target آخر لمجرد تشابه الاسم.

### Row boundary

كل hit يحمل `TargetProduct` من catalog نفسه. أي evidence خارجي يربط اسمًا فقط؛
لا يتحول إلى product payload أو price أو availability.

### Diagnostic boundary

diagnostics القادمة من matching عام لا تُقبل إلا بعد resolve إلى صف فعلي في
`catalog_by_id` الحالي. عند وجود نفس `store_product_id` في عدة rows يجب الحفاظ
على كل rows المميزة بالـ source/row/name وعدم اختيار أول صف اعتباطيًا.

### Artifact boundary

في CSV/JSONL يجب أن تكون القيم صريحة:

```text
source_kind = excel-target
target_key  = البركة شركات
source_file = محروس1.xlsx
source_row  = 3100
```

ولا يكفي أن يظهر `matching_source_label` دون row-level provenance. يجب أن يكون
أي عرض من UI قابلًا للتتبع إلى نفس `excel_target_row_key` الذي استُعمل في
deduplication.

### Multi-target boundary

إذا شُغلت البركة والقيصر في نفس order run، يبقى لكل target index وartifact
منفصلان. لا ينبغي أن تتشارك aliases أو candidate rows إلا عبر immutable
evidence عامة، مع بقاء materialized rows target-scoped.

## سلامة automatic matching

هذه القواعد non-negotiable:

1. **Review-only type separation:** كل hit من transliteration أو cached
   translation أو cross-language fuzzy يحمل kind لا تقبله automatic acceptance.
2. **Separate input sets:** `_compatible_identified` لا يستقبل review-only
   candidates؛ يتم تمريرها إلى `build_review_candidates` فقط.
3. **No auto-save from review evidence:** لا ينشئ candidate review-only قرارًا
   محفوظًا إلا بعد اختيار بشري scoped إلى target/row.
4. **No silent alias promotion:** manual approval ينتج alias proposal أو exact
   row correction، وليس global alias فوريًا.
5. **Ambiguity remains ambiguity:** إذا أعاد alias أو transliteration أكثر من
   brand/row متقارب، يجب أن يبقى `best_match=None` ويُعرض الجميع ضمن limit.
6. **Compatibility is explanatory:** اختلاف القوة/الشكل/العبوة لا يحذف الصف
   من review إذا كان brand evidence قويًا، لكنه يمنعه من automatic acceptance.
7. **Provider isolation:** لا live translation أو external search داخل index
   builder أو per-item discovery دون flag صريح ومسار audit مستقل.
8. **Regression gate:** أي تعديل recall يجب أن يثبت أن عدد automatic matches
   وقراراتها لا يتغير في replay safety suite، أو أن كل تغير موثق ومقبول.

## استراتيجية الترتيب وزيادة عدد المرشحين

رفع `manual_review_save_candidate_limit` وحده لا يكفي؛ المرشح الذي لم يدخل
evidence set لن يعيده writer. يلزم فصل ثلاثة حدود:

| الحد | الوظيفة المقترحة |
|---|---|
| retrieval limit | أقصى عدد rows تستخرجه كل channel قبل الدمج |
| merge/diversity limit | عدد rows بعد dedup مع quota لكل channel |
| save/display limit | عدد options المحفوظة أو المعروضة في artifact/UI |

لمنع سيطرة fuzzy channel على القائمة، يمكن استعمال quotas مثل:

```text
audited identity: up to 10
cached translation: up to 5
transliteration: up to 5
same-script fuzzy: up to 10
final saved limit: configured 30
```

هذه أرقام تصميمية وليست قيمًا يجب تثبيتها قبل replay. الأهم أن كل option يحتفظ
بـ `candidate_method` وسبب ظهوره، وأن ranking لا يقارن score من قنوات مختلفة
وكأنها مقياس واحد.

## المخاطر والضوابط

| الخطر | كيف يحدث | الضابط المقترح |
|---|---|---|
| زيادة noise بدل recall المفيد | transliteration أو fuzzy يلتقط تشابهًا عامًا | minimum meaningful anchor، runner-up margin، وgold negatives |
| collision بين aliases | alias واحد يشير إلى أكثر من brand أو variant | target-scoped graph، ambiguity status، ومنع automatic acceptance |
| حذف جزء من البراند | تطبيع يزيل `س`, `PLUS`, `XR`, أو digits meaningful | normalizer منفصل review-only واختبارات negative لكل token حساس |
| خلط صف Excel مع مصدر خارجي | diagnostic أو dictionary row يدخل artifact | row must resolve إلى catalog الحالي مع source/row invariant |
| تفاوت scores بين القنوات | fuzz ratio وtranslation similarity غير قابلين للمقارنة | channel priority + calibrated per-channel score، لا sort score فقط |
| latency/provider failure | live translation داخل discovery | cache-only index، batch precompute، وtimeout/feature flag |
| candidate explosion | brand شائع أو catalog كبير | per-channel retrieval limit، diversity، pagination، وmetrics للضوضاء |
| تلوث automatic path | تمرير tuple review إلى identity compatibility | types/evidence kind واختبار صريح أن best match يظل None |
| stale translation cache | model قديم أو ترجمة غير صحيحة | model/version provenance، expiry أو shadow comparison |
| تغيير غير قابل للتفسير | alias أو normalization يتغير دون أثر | artifacts تحتوي channel/canonical/source/version وreplay snapshots |

## الاختبارات المقترحة

### Unit tests للفهرس

1. English query مع Arabic-only target row وTawreed/dictionary alias موثق:
   يظهر `ReviewDiscoveryHit` بالـ source/row الصحيح.
2. English query مع Arabic-only row بلا alias:
   لا يظهر cross-language hit لمجرد تشابه attributes العامة.
3. Arabic query مع English-only target row والعكس، مع نفس سياسة عدم الخلط
   التلقائي.
4. Mixed-script query ينتج views متعددة deterministic، ولا يعتمد على أول span.
5. Transliteration positive gold مثل `AGGREX` ↔ `اجركس` إذا اعتمدت القاعدة،
   وnegative مثل `ACTOS` ↔ `سالبوفنت` لا يمر.
6. Alias collision يعيد كل rows المميزة ولا يحول أيًا منها إلى automatic
   winner.
7. نفس `store_product_id` في صفين مختلفين يحافظ على source/row/name لكل صف.
8. duplicate physical row يزال deduplicated بالـ row key.
9. status/decoration مثل `س جديد` لا يحذف brand ينتهي فعلًا بـ `س`.
10. attribute conflict يبقى ظاهرًا مع `compatibility_rejection` بدل اختفائه.
11. ترتيب النتائج ثابت مع نفس catalog حتى عند اختلاف ترتيب input rows.
12. index لا يستدعي live translation/network provider أثناء `discover`.

### Integration tests للمطابق

1. `matcher.match` لا يغير `best_match` بسبب review-only hit.
2. المرشح review-only يدخل `review_candidates` مع `candidate_method` وevidence
   صحيحين.
3. diagnostic من target آخر أو صف غير موجود يُرفض من builder.
4. تشغيل targetين في نفس الأمر لا يخلط rows أو aliases أو artifact paths.
5. saved approval يظل exact/scoped ولا يتحول إلى alias عام.
6. `candidate_count_total` يساوي عدد المرشحين بعد الدمج وقبل save limit.
7. `candidate_count_saved` يساوي options الفعلية في JSONL، مع حفظ row keys.
8. وجود مرشح compatible في القائمة لا يفتح automatic match إذا كان channel
   review-only.

### Replay وقياس الجودة

على run تاريخي مصنف، خصوصًا run الـ 2397 item، يجب حفظ before/after بنفس:

- input items.
- target workbooks.
- config thresholds.
- saved approvals policy.
- execution mode وlimit.

المقاييس المطلوبة:

| المقياس | الهدف |
|---|---|
| `candidate_recall@1/@5/@10/@30` | كم مرة ظهر الصف الذي اختاره المراجع داخل أول N خيارات |
| cross-language rescue rate | نسبة الحالات التي أنقذها channel عربي/إنجليزي أو transliteration |
| manual-review coverage | نسبة الحالات التي دخلت review مع مرشح واحد على الأقل |
| useful-candidate precision | نسبة options التي يعتبرها المراجع مفيدة |
| noise per item | متوسط الخيارات غير المفيدة لكل item |
| automatic decision delta | يجب أن يساوي صفرًا في shadow phase |
| source-leak count | يجب أن يساوي صفرًا |
| p95 latency/build cost | للتأكد أن تعدد projections لا يبطئ التشغيل المقبول |

## مراحل التنفيذ المقترحة لاحقًا

### Phase 0: shadow analysis

- بناء cross-language index في مسار read-only أو script replay.
- لا تغيّر `review_candidates` ولا automatic decisions.
- اكتب artifact إضافيًا يحتوي القنوات والمرشحين الذين كان يمكن استدعاؤهم.
- راجع عينات high-recall وhigh-noise يدويًا.

### Phase 1: audited bilingual expansion

- إدخال Tawreed/dictionary aliases target-scoped إلى review discovery.
- اعتماد row-aware provenance وreview-only evidence.
- تشغيل regression suite الخاصة بالبركة والقيصر وجميع negative aliases.

### Phase 2: cached translation channel

- استعمال cache الموجود فقط، بلا provider calls أثناء item matching.
- إضافة model/source/age إلى evidence.
- قياس precision منفصلًا عن exact aliases.

### Phase 3: transliteration channel

- اختيار scheme واحدة deterministic.
- بناء gold set للأسماء العربية ذات الأصل اللاتيني وnegative set للأسماء غير
  القابلة للاستنتاج.
- تشغيله خلف feature flag وبـ review-only status مستقل.

### Phase 4: identity-absent discovery

- السماح بإدخال بعض `identity_absent` إلى manual review إذا كان لديها anchor
  قوي من قناة cross-language أو same-script.
- لا تستخدم هذا كـ fallback broad لكل catalog؛ يجب أن يخضع لـ recall/noise
  gates وpagination.

## معايير الإيقاف والقبول

لا تُرفع التغييرات إلى automatic matching إلا إذا تحققت جميع الشروط التالية:

- المرشح الصحيح يظهر في gold replay ضمن configured N.
- لا توجد source leaks بين Excel targets.
- لا توجد زيادة غير مبررة في automatic matches أو auto-saves.
- كل review-only candidate يحمل provenance وسببًا قابلًا للتفسير.
- negative transliteration/alias cases لا تتحول إلى winners.
- p95 latency وذاكرة الفهرس مقبولان على catalogات الإنتاج.
- يمكن تعطيل كل channel منفصلًا من config أو feature flag.

## الخلاصة التصميمية

المطلوب ليس تحويل `ExcelTargetReviewDiscoveryIndex` إلى fuzzy search شامل، بل
تعميقه خلف interface صغيرة تجمع projections متعددة وتعيد evidence قابلة
للمراجعة. أفضل seam هو أن يبقى catalog/row provenance داخل Excel-target
adapter، بينما تبقى aliases والترجمة وtransliteration مجرد قنوات evidence.

بهذا نكسب recall عبر اللغات دون التضحية بالسلامة:

```text
English/Arabic/mixed query
        ↓
review-only cross-language projections
        ↓
target-scoped row validation
        ↓
ranked, diverse manual-review candidates
        ↓
human decision only
```

ولا يجوز أن يصبح المسار:

```text
transliteration/translation score → automatic Excel match
```

لأن ذلك يخلط بين استدعاء مرشح مفيد للمراجع وبين إثبات هوية صالح لاتخاذ قرار
شراء تلقائي.
