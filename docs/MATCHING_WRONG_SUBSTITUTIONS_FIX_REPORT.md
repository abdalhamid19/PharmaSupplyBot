# تقرير إصلاح مطابقات المنتجات الخاطئة

> التاريخ: 2026-07-05  
> النطاق: إصلاح ست حالات matching خاطئة كانت تختار منتجاً مختلفاً عن الصنف المطلوب.  
> معيار النجاح: كل حالة من الحالات المذكورة يجب ألا تتحول إلى `best_match` قابل للتنفيذ.

## الخلاصة التنفيذية

تمت معالجة المشكلة بإضافة اختبارات regression للحالات الست، ثم تعديل قواعد المطابقة في أضيق نطاق ممكن. السبب المشترك لم يكن عطلاً في البحث نفسه، بل أن طبقة `components_match` كانت متساهلة مع اختلافات مهمة في الهوية، الشكل الدوائي، أو المكون المطلوب.

النتيجة بعد الإصلاح:

| الكود | الصنف المطلوب | المنتج الخاطئ | النتيجة بعد الإصلاح |
|---|---|---|---|
| 92558 | LIMITLESS MILGA MAX 30 TABS | LIMITLESS MAN MAX 30 TABS | مرفوض: `different_modifier` |
| 77101 | GARAMYCIN OINT 15GM | GARAMYCIN 0.1 % CREAM 15 GM | مرفوض: `different_form` |
| 34157 | DIPROSONE OINT | DIPROSONE 0.05 % CREAM 30 GM | مرفوض: `different_form` |
| 80838 | CO_AVAZIR 5GM EYE OINTMENT | AVAZIR 0.3 % EYE DROPS 10 ML | مرفوض: `different_form` |
| 79407 | LILI FEMININE WASH 250ML | LILIOX 10 SACHETS | لا يوجد match قابل للتنفيذ |
| 58580 | ISIS CINNAMON WITH GINGER 20 BAG | ISIS CINNAMON 20 FILTER BAGS | مرفوض: `different_flavor` |

## شرح سبب المشكلة بالتفصيل

### 1. LIMITLESS MILGA MAX مقابل LIMITLESS MAN MAX

كان parser يقرأ الاسمين كعلامتين متقاربتين:

```text
LIMITLESS MILGA MAX 30 TABS -> brand = LIMITLESSMILGAMAX
LIMITLESS MAN MAX 30 TABS   -> brand = LIMITLESSMANMAX
```

منطق `_brand_match_check` يسمح أحياناً باختلاف داخل brand إذا كانت نسبة fuzzy كافية أو يوجد احتواء جزئي. وبما أن `MAX` مشترك والاسم قريب، لم يكن هناك token حاسم يقول إن `MILGA` و`MAN` variant مختلفان.

الإصلاح: أضفت `MILGA` و`MAN` إلى `CRITICAL_MODIFIERS` حتى تصبح اختلافاً دوائياً/تجارياً حاسماً. الآن اختلافهما يرجع `different_modifier` ولا يسمح بالاختيار.

### 2. GARAMYCIN OINT مقابل GARAMYCIN CREAM

المشكلة هنا أن `OINT` اختصار `OINTMENT` ولم يكن ضمن ترتيب forms التي يمسحها parser. نتيجة ذلك:

```text
GARAMYCIN OINT 15GM -> form فارغ أو غير حاسم
GARAMYCIN CREAM     -> form = CREAM
```

وعندما يكون أحد الطرفين بلا form واضح، `_other_match_check` لا يستطيع رفض اختلاف الشكل.

الإصلاح: أضفت `OINT` و`OINTMENT` إلى `FORM_SCAN_ORDER`، وأضفت canonical form باسم `OINT`. الآن `OINT` مقابل `CREAM` ينتج `different_form`.

### 3. DIPROSONE OINT مقابل DIPROSONE CREAM

هذه نفس عائلة الخطأ السابقة. الصنف المطلوب مرهم، والمرشح كريم. قبل الإصلاح لم يكن `OINT` شكلاً دوائياً مفهوماً بما يكفي، لذلك قبل النظام الكريم.

الإصلاح نفسه يحلها: `OINT/OINTMENT` أصبحا form مستقلين وغير متوافقين مع `CREAM`.

### 4. CO_AVAZIR EYE OINTMENT مقابل AVAZIR EYE DROPS

هذه أخطر من مجرد اختلاف اسم. المطلوب مرهم عين، والمرشح قطرة عين. قبل الإصلاح كان parser يعطي أولوية لكلمة `EYE` قبل أن يتعرف على `OINTMENT` كالشكل الأساسي، فبدا الشكل قريباً من قطرات العين.

الإصلاح: وضعت `OINTMENT` و`OINT` قبل `EYE/DROPS` في ترتيب `FORM_SCAN_ORDER`. الآن `CO_AVAZIR 5GM EYE OINTMENT` يصبح form = `OINT`، و`AVAZIR EYE DROPS` يصبح form = `EYE`. النتيجة `different_form`.

### 5. LILI FEMININE WASH مقابل LILIOX SACHETS

هذه كانت مطابقة خاطئة من ناحية الهوية. في القياس الحالي قبل الإصلاح لم تتحول إلى best match بسبب numeric rejection، لكنها كانت ضمن نفس نمط المخاطر: اسم قريب لكن منتج مختلف تماماً.

أضفتها كاختبار regression ضمن نفس المجموعة حتى لا تتحول مستقبلاً إلى match إذا تغيرت درجات scoring أو numeric acceptance.

### 6. ISIS CINNAMON WITH GINGER مقابل ISIS CINNAMON فقط

المطلوب يحتوي على `GINGER`، والمرشح لا يحتوي عليه. قبل الإصلاح `GINGER` لم يكن ضمن `FLAVOR_WORDS`، لذلك لم يعتبره النظام مكوناً/نكهة مميزة مطلوبة.

الإصلاح: أضفت `GINGER` إلى `FLAVOR_WORDS` وغيرت منطق flavor بحيث الاختلاف يشمل حالة وجود flavor في طرف وغيابه في الطرف الآخر. الآن حذف `GINGER` ينتج `different_flavor`.

## الملفات المعدلة

### `src/core/drug_matching/normalization/normalizer_constants.py`

التغييرات:

1. إضافة `GINGER` إلى `FLAVOR_WORDS`.
2. إضافة `MAN` و`MILGA` إلى `CRITICAL_MODIFIERS`.
3. إضافة `OINTMENT` و`OINT` إلى `FORM_SCAN_ORDER` قبل `EYE/DROPS`.

### `src/core/drug_matching/normalization/normalizer_parsing_parse.py`

التغييرات:

1. جعل `_canonical_form` يرجع `OINT` عند رؤية `OINT` أو `OINTMENT`.
2. تنسيق سطر طويل قديم في return الخاص بالحالة الفارغة حتى لا يزيد مخالفات audit.

### `src/core/drug_matching/normalization/normalizer_matching_form.py`

التغيير:

1. كان flavor يرفض فقط إذا كان الطرفان لديهما flavor مختلف.
2. أصبح يرفض أيضاً إذا كان flavor موجوداً في الطلب ومفقوداً من المرشح، أو العكس.

### `tests/test_latest_no_results_regressions.py`

التغيير:

1. إضافة اختبار `test_reported_wrong_matches_are_rejected`.
2. الاختبار يغطي الحالات الست المذكورة ويؤكد أن `decision.best_match is None`.

## لماذا هذا الإصلاح محدود وآمن

لم أضف طبقة matching جديدة ولم أغير scoring العام. التعديل اقتصر على تعريف tokens كانت ناقصة في parser أو modifier lists، وعلى جعل اختلاف flavor أكثر صرامة عندما تكون النكهة/المكون صريحة في اسم الصنف.

هذا أفضل من رفع thresholds أو تعطيل fuzzy matching، لأن رفع thresholds قد يكسر مطابقات صحيحة كثيرة، بينما هذه الحالات كلها اختلافات semantic واضحة:

1. `MILGA` ليس `MAN`.
2. `OINT/OINTMENT` ليس `CREAM`.
3. `EYE OINTMENT` ليس `EYE DROPS`.
4. `WITH GINGER` ليس Cinnamon فقط.

## نتائج التحقق

### اختبار الحالات الست

```powershell
python -m pytest tests\test_latest_no_results_regressions.py::LatestNoResultsRegressionTests::test_reported_wrong_matches_are_rejected -q
```

النتيجة:

```text
1 passed, 6 subtests passed
```

### اختبارات matching المركزة

```powershell
python -m pytest tests\test_latest_no_results_regressions.py tests\test_product_matching.py tests\core\drug_matching\test_drug_matching_normalizer.py tests\test_manufacturer_mismatch.py -q
```

النتيجة:

```text
63 passed, 115 subtests passed
```

### كل الاختبارات

```powershell
python -m pytest tests -q --ignore=tools
```

النتيجة:

```text
431 passed, 20 skipped, 2 warnings, 123 subtests passed
```

التحذيرات الموجودة من pytest تخص اختبارات قديمة ترجع `bool` بدلاً من `None`، وليست ناتجة عن هذا التعديل.

### rule audit

```powershell
python tools\rule_audit.py
```

النتيجة: الأداة ما زالت تعرض مخالفات قديمة كثيرة في المشروع. لم تكن هذه المخالفات ضمن نطاق إصلاح المطابقات الست، والاختبارات الوظيفية كلها ناجحة. تم تقليل أثر تعديلي بعدم إضافة مخالفات غير ضرورية في الملفات التي لمستها.

## الخلاصة

المشكلة كانت أن parser وقواعد component matching لم تكن صارمة بما يكفي مع اختلافات semantic ظاهرة. بعد التعديل، الحالات الست لم تعد تتحول إلى `best_match`، وبالتالي لن يضيف النظام منتجاً مختلفاً للسلة بناءً على هذه المطابقات الخاطئة.
