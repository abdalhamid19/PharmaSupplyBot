# حلول ممكنة ومقارنة اختيارها

## قيود لا تنازل عنها

- لا auto-match لصف Arabic-only بلا دليل brand identity.
- لا نكسر exact English Excel targets.
- لا يعتمد matcher أو trace loop على Cohere live؛ quota أو الشبكة لا تحدد سلامة الطلب.
- الحالات غير المثبتة تذهب إلى `no-results` أو manual review تحت `--flagged-match-action manual-review-only`.
- كل حل يمرر scorecard ثم كامل اختبارات matching.

| البديل | التغيير | precision | recall العربي | التعقيد | القرار |
|---|---|---:|---:|---:|---|
| A | استدعاء `acceptance_details` فقط | أعلى من الحالي | منخفض/غير مضمون | منخفض | خطوة أمان لازمة لا تكفي |
| B | إعادة identity guard لكل Excel target | عالٍ | قد يهبط جدًا | منخفض | kill switch مؤقت فقط |
| C | قبول source-aware: bilingual identity مثبت ثم thresholds | عالٍ جدًا | جيد بعد cache/dictionary | متوسط | **المفضل** |
| D | mapping يدوي `(item code -> target code)` | أقصى دقة للصفوف المعتمدة | محدود ويتطلب صيانة | متوسط | override مكمل |
| E | تغيير YAML أو Cohere threshold فقط | ضعيف | متذبذب | منخفض | مرفوض كحل أساسي |

## الحل المفضل C

1. استخدم عقد thresholds الموجود لكل candidate؛ لا تنسخه.
2. ميّز بين `productNameEn` الحقيقي واسم Excel الخام. Arabic-only row لا يدّعي اسمًا إنجليزيًا.
3. قبل canonical auto-accept لصف Arabic-only، اطلب dictionary hit قوي أو cached translation بbrand similarity موثق أو manual-review decision يطابق target code/name أو حقل bilingual verified في source.
4. طبق form/strength/pack بعد إثبات brand، لا قبله.
5. عند غياب الإثبات، أعد سببًا واضحًا مثل `Arabic-only candidate lacks verified brand identity`.

## لماذا ليس B وحده

إزالة الاستثناء ستحمي من false positives، لكن حارس identity الحالي إنجليزي واسم البركة عربي؛ قد يتحول كل matching إلى no-results حتى الصفوف الصحيحة. لذا B آمن عند الطوارئ، لكنه لا يحقق وظيفة bilingual المطلوبة.

## اختبار البدائل

يطبق كل بديل في branch مستقل. يمرر أولًا scorecard (precision، exact-English recall، determinism)، ثم replay Excel-only لأول 50، ثم مراجعة كل Arabic-only auto-match مع evidence. لا يحق للأمر الأصلي `--match-only --execution-mode api` أن يعمل قبل نجاح replay.

