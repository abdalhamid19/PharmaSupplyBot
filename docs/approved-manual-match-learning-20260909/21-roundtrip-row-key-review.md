# مراجعة Gate 0: مسار `row-key` و`ranking_tier`

## نطاق المراجعة

تم فحص الـ workspace الحالي بعد تغييرات Gate 0، مع التركيز على المسار:

`Excel-target writer → JSONL → load_review_candidates → Streamlit merge/render`

لم يتم تعديل كود الإنتاج أو الاختبارات أو `state`. تم تشغيل الاختبارات الموجودة فقط:

```text
37 passed in 1.65s
```

## الحكم المختصر

| الحقل | JSONL writer | loader/model | Streamlit merge | النتيجة العملية |
|---|---|---|---|---|
| `excel_target_row_key` | يكتب | يُقرأ ويُحفظ | يدخل في dedup ولا يُفقد | يمر كاملًا، لكن عرضه للمراجع جزئي |
| `ranking_tier` | يكتب | يُحوّل إلى `int` ويُحفظ | يبقى داخل الكائن | يمر كـ metadata فقط؛ لا يُستخدم لترتيب أو ضمان الظهور |

الخلاصة: إصلاح Gate 0 أغلق مشكلة إسقاط صفين مختلفين لهما نفس المنتج/الاسم في طبقتي store وUI، لكنه لم يجعل `ranking_tier` سياسة ترتيب في Streamlit. كما أن row key موجود داخل الخيار، لكنه ليس جزءًا من label لكل اختيار، وملخص provenance قد يعرض row key واحدًا فقط لكل scope.

## الأدلة حسب المرحلة

### 1. نموذج `ReviewCandidateOption`

في `src/core/manual_review/manual_review_candidates.py:24-56` يوجد الحقلان:

- `excel_target_row_key: str = ""` في السطر 54.
- `ranking_tier: int = 4` في السطر 56.

`to_dict()` يستعمل `dataclasses.asdict` في السطرين 58-60، ولذلك يضمّن الحقلين تلقائيًا.

في `from_dict()`:

- row key القياسي يُقرأ في السطرين 78-79، مع fallback من `target_row_key`.
- `ranking_tier` يُحوّل إلى integer في السطور 98-101، والقيمة الافتراضية للـ artifacts القديمة هي `4`.
- التصفية النهائية في السطرين 102-103 لا تسقط أيًا من الحقلين لأنهما dataclass fields.

النتيجة في هذه الطبقة: **PASS**.

### 2. كاتب Excel-target وJSONL

في `src/core/excel_target/excel_target_review_candidates.py:143-187`:

- `to_review_candidate_dict()` يكتب `ranking_tier` في السطر 179.
- يكتب `excel_target_row_key` في السطر 185.
- يكتب رقم الصف الأصلي في السطر 186.

ثم `src/cli/commands/cli_order_excel_target.py:653-673` يكتب هذا القاموس داخل `options` في JSONL. أما الكاتب العام في `src/core/manual_review/manual_review_candidate_store.py:12-28` فيستعمل `opt.to_dict()`، وبالتالي يضمّن الحقلين أيضًا عند استخدامه مع خيارات Tawreed أو legacy.

النتيجة في الـ writer: **PASS**.

### 3. Loader وdedup

في `src/core/manual_review/manual_review_candidate_store.py:65-75` يتم إنشاء `ReviewCandidateOption` بواسطة `from_dict()`، لذلك لا تضيع قيمة row key أو tier أثناء القراءة.

في dedup داخل السطور 79-92، هوية الخيار تشمل:

```text
store_product_id,
name_en,
name_ar,
matching_source,
target_key,
source_file,
excel_target_row_key
```

إضافة `excel_target_row_key` في السطر 87 تعني أن صفين ماديين مختلفين لا يندمجان لمجرد تشابه product id أو الاسم. في المقابل، `ranking_tier` ليس جزءًا من هوية dedup، وهذا صحيح عادةً: اختلاف tier لنفس الصف لا ينبغي أن ينشئ اختيارًا ثانيًا.

ملاحظة حدودية: إذا وصل artifact قديم بلا row key، فسيظل يعتمد على بقية الهوية، وقد يندمج صفان متطابقان تمامًا في الحقول القديمة. لا يوجد حاليًا رفض صريح لخيار Excel-target الذي يملك `source_row` بلا row key قابل للتحقق.

النتيجة في loader: **PASS مع فجوة اختبارية**.

### 4. Streamlit merge والاختيار

في `src/ui/manual_review/streamlit_manual_review_page.py:244-270`:

- `_load_group_candidates()` يعيد خيارات typed من loader.
- هوية dedup في السطور 256-265 تشمل `excel_target_row_key` في السطر 264.
- `_candidate_with_run_source()` يستخدم `dataclasses.replace` في السطور 281-299؛ لذلك لا يسقط row key أو ranking tier عند إضافة provenance legacy.

وعند حفظ الاختيار، `src/core/manual_review/manual_review_selection.py:41-60` ينقل:

- `excel_target_row_key` في السطر 58.
- `excel_target_source_row` في السطر 59.

إذًا row key لا يمر فقط إلى UI، بل يمر أيضًا إلى `ManualReviewDecision` عند اعتماد الخيار.

النتيجة في merge/save: **PASS**.

## الفجوات المهمة في الواجهة

### `ranking_tier` لا يتحكم في الترتيب

في `streamlit_manual_review_page.py`:

- `render_run_candidates()` يمرر الخيارات إلى `_limit_candidates_by_source()` في السطور 235-241.
- `_limit_candidates_by_source()` يحافظ على ترتيب القائمة الوارد من artifact؛ لا توجد مقارنة بـ`ranking_tier`.
- `_build_radio_opts()` في السطور 664-679 لا يعرض tier ولا يعيد الترتيب بناءً عليه.

بالتالي القيمة تصل إلى الواجهة داخل `ReviewCandidateOption`، لكنها لا تمنع أن يسبق tier-4 خيارًا من tier-2 إذا كان ترتيب JSONL/merge كذلك. هذا يحقق round-trip للبيانات، لا يحقق سياسة ranking في الواجهة.

### row key موجود، لكن ظهوره للمراجع غير كامل

`_render_candidate_provenance()` في السطور 433-471 يعرض row key في السطر 470، لكن `scopes` في السطور 435-445 لا يتضمن row key ضمن مفتاح التجميع. لذلك إذا كان لنفس source/target/evidence أكثر من physical row، يعرض ملخص provenance خيارًا ممثلًا واحدًا فقط.

كذلك `_build_radio_opts()` في السطور 664-679 لا يضع row key في label كل اختيار. لذلك قد يرى المراجع عدة صفوف متشابهة دون معرف الصف الفعلي، رغم أن الاختيار الداخلي سيحفظ row key الصحيح.

الحكم على visibility: **PARTIAL**؛ transport صحيح، لكن auditability البصرية لكل physical row غير مكتملة.

## الاختبارات الموجودة وما تغطيه

1. `tests/core/manual_review/test_manual_review_candidates.py:160-206` يختبر round-trip مباشرًا لـ`ReviewCandidateOption.to_dict()`/`from_dict()` مع row key وtier.
2. `tests/cli/commands/test_excel_target_manual_review_artifacts.py:152-210` يختبر الفرق بين `candidate_count_total` و`saved cap`، لكنه لا يثبت بقاء صفين متطابقين في الاسم مع row keys مختلفة.
3. `tests/ui/manual_review/test_streamlit_manual_review.py:339-370` يختبر دمج Tawreed وExcel-target، و`584-614` يختبر display cap وتنوع المصادر، لكن لا يختبر row-key uniqueness أو ranking-tier ordering.

هذه الاختبارات نجحت كلها في التشغيل الحالي (`37 passed`)، لكنها لا تثبت المسار الكامل writer → JSONL file → loader → UI merge لصفين متشابهين.

## الاختبارات اللازمة قبل إغلاق Gate 0

### A. اختبار round-trip فعلي عبر JSONL

أنشئ خيارين لهما نفس:

```text
store_product_id, name_en, name_ar, matching_source, target_key, source_file
```

لكن لهما `excel_target_row_key` مختلف و`excel_target_source_row` مختلف، و`ranking_tier` مختلف. اكتب artifact ثم استعمل `load_review_candidates()`، ويجب إثبات:

- بقاء الخيارين، لا خيار واحد.
- بقاء row key ورقم الصف لكل خيار.
- بقاء `ranking_tier` لكل خيار.

### B. اختبار writer الخاص بـExcel-target

استعمل `ExcelTargetReviewCandidate` و`_append_excel_target_review_artifacts()`، ثم اقرأ سطر JSONL كـraw JSON قبل تمريره للـmodel. يجب التحقق من وجود:

```text
options[*].excel_target_row_key
options[*].excel_target_source_row
options[*].ranking_tier
```

هذا يمنع أن ينجح model round-trip بينما يكون writer الحقيقي قد غيّر أسماء الحقول أو أسقطها.

### C. اختبار UI merge مع physical rows متشابهة

مرّر إلى `_load_group_candidates()` خيارين متطابقين في الاسم وproduct id لكن مختلفين في row key. يجب أن يبقى الاثنان، ثم تحقق من أن اختيار كل index ينتج `ManualReviewDecision` يحمل row key المطابق، لا row key للخيار الآخر.

### D. اختبار duplicate الحقيقي مقابل duplicate المادي

- نفس row key في ملفين: يُدمج إلى خيار واحد.
- row keys مختلفة: يبقيان خيارين.
- row key فارغ مع بيانات متطابقة: يوثق بوضوح هل legacy dedup مقبول أم يجب رفض artifact ناقص provenance.

### E. اختبار سياسة tier في الواجهة

إذا كان المقصود أن `ranking_tier` يوجّه ما يراه المراجع، أضف اختبارًا يضع tier-2 بخلاف score أعلى/tier-4، ثم يثبت أن الترتيب النهائي يضع tier-2 أولًا وأن display cap لا يسقطه. أما إذا كان tier سيبقى metadata فقط، فيجب توثيق ذلك صراحة وعدم اعتباره ranking فعّالًا.

### F. اختبار visibility/auditability

أنشئ خيارين من نفس source/target/evidence لكن row keys مختلفة، واستدعِ `_render_candidate_provenance()` مع mock لـStreamlit. يجب تحديد السلوك المطلوب: عرض كل row key، أو الاكتفاء بعرضه داخل label لكل radio option. الوضع الحالي يعرض ممثلًا واحدًا في provenance summary ولا يعرضه في radio label.

## التوصية

لا توجد مشكلة round-trip تمنع الانتقال إلى الاختبار التالي: row key وranking tier يصلان إلى loader وUI object، وrow key يدخل في dedup والحفظ. لكن Gate 0 لا ينبغي اعتباره مغلقًا بالكامل قبل إضافة اختبار JSONL الحقيقي واختبار physical-row dedup.

وقبل أي توسعة candidate recall إضافية، يجب اتخاذ قرار صريح بشأن `ranking_tier`:

1. إما تحويله إلى ترتيب UI فعلي مع test يثبت عدم سقوط tier-2 تحت display cap.
2. أو إبقاؤه metadata للتدقيق فقط، مع عدم الادعاء أن الواجهة تستخدمه في ranking.
Gate 0 follow-up: row-key and ranking metadata are now covered by the local round-trip regression tests.
