# تنفيذ والتحقق من إصلاح مطابقة البركة

تاريخ التنفيذ والتحديث الأخير: 2026-09-07.

## ما تم إصلاحه

- لم يعد الاسم العربي الخام يُكتب في `productNameEn`. الاسم الإنجليزي الأصلي
  فقط هو الذي يستخدم هذا الحقل.
- مسار Excel Target أصبح offline بالكامل: لا يستدعي `match_brand_readonly`
  ولا fuzzy Tawreed ولا Cohere أثناء المطابقة.
- بُني فهرس bilingual واحد عند تحميل الكتالوج، ويستخدم فقط:
  native English، dictionary direct hit، cached translation exact brand، أو
  Tawreed alias مربوط بصف موجود فعلياً في كتالوج البركة.
- لا يُستخدم `tawreed_products.csv` كمصدر توافر أو سعر أو كمرشح مستقل؛ دوره
  alias ثنائي اللغة فقط، ثم يعود القرار إلى صف Baraka نفسه.
- لا يكفي تطابق العلامة وحده: اختلاف أو غياب الشكل الدوائي أو التركيز أو العبوة
  يؤدي إلى no-results/manual review.
- قرار manual review القديم غير المقيد لا يفرض نتيجة Excel Target. الاستثناء
  يتطلب target key وstore product id صريحين.
- أضيفت أعمدة evidence وcompatibility وزمن المطابقة إلى CSV، وJSONL واحد لكل
  input item. أضيف خيار `--excel-target-only` لمنع تشغيل Tawreed في replay.

## اختبارات آلية ناجحة

```text
87 passed, 8 subtests passed in 27.41s
```

هذه البوابة تشمل اختبارات attributes الجديدة، safety regression، Excel target،
CLI، manual review، product matching، وscorecard التشخيصي.

اختبارات السلامة الجديدة تثبت رفض:

- `INODEP CAPSULES 30` مقابل إنوديب شراب 100 مل.
- إنوديب 1000 مجم.
- إنوديب 20 كبسول.

وتثبت قبول إنوديب 30 كبسول فقط عندما يوجد دليل dictionary/cache حقيقي.

## تشغيلات تاريخية وخط الأساس

التشغيلات المؤرخة في `20260906_1822` و`20260906_1828` كانت baseline قبل
إضافة aliases والتطبيع اللاحقين، وسجلت 4 matches و46 no-results. نحتفظ بها
للمقارنة التاريخية فقط؛ لا تمثل النتيجة النهائية الحالية.

## آخر replay بعد تنفيذ المرحلة 3 وcoverage

تم تشغيل Excel-only replay نهائي في:

- `artifacts/excel-target/البركة شركات/20260907_1558/match_only_summary_البركة شركات.csv`
- `artifacts/excel-target/البركة شركات/20260907_1558/match_only_summary_البركة شركات.jsonl`

النتيجة: 50 صفاً، 13 `matched-only` و37 `no-results`. كل المطابقات الثلاث عشرة تحمل
`compatibility_status=compatible`، ومصادر الهوية هي 5 dictionary و7
`tawreed_catalog` و1 cached translation. أسباب الرفض للـ37 هي 29 نقص دليل هوية،
و8 حالات variant/compatibility مرفوضة. لا يوجد أي `matched-only` مع compatibility
غير متوافقة.
تفصيل الرفض المتبقي: 4 خصائص strength غير مثبتة، حالتا strength متعارضتان،
حالة form غير مثبتة، وحالة pack متعارضة.
وأُعيد فحص الحالات الثماني ذات الهوية الموجودة على كل variants المفهرسة؛
لم توجد أي variant إضافية متوافقة يمكن قبولها بأمان.
الإضافة الأخيرة هي `ASMAKAST 10 MG 30 TAB` إلى صف `ازماكست 10 مجم 30 قرص`
بعد توثيق اختلاف التهجئة `ازماكاست/ازماكست` واختبار اختيار قوة 10 مجم دون
قبول صف 5 مجم.
كل صف من الصفوف الخمسين يحمل الآن `match_elapsed_ms` في CSV وJSONL، بما في ذلك
حالات `no-results`.

وقياس الجلسة محفوظ في `artifacts/excel-target/البركة شركات/20260907_coverage/baraka_index_benchmark.json`:
فهرس catalog البالغ 4,107 صفاً بُني مرة واحدة في `6741.93ms`، ثم تمت مطابقة
50 item في `747.14ms` فقط؛ أي أن زمن الجلسة نحو `7.49s` وأقل من حد 300 ثانية.

## آخر تشغيل للأمر الأصلي

بعد نجاح Excel-only replay تم تشغيل الأمر الأصلي الذي يجمع `--all-profiles`
و`--execution-mode api` مع `--match-only`. اكتمل في 50 ثانية، وسجل Tawreed
`processed=50, matched=47, flagged=1`، بينما سجل Baraka في نفس التشغيل:
`processed=50, matched=13, flagged=37`.

أُعيدت مراجعة artifact Baraka النهائي:

- `artifacts/excel-target/البركة شركات/20260907_1600/match_only_summary_البركة شركات.csv`
- `artifacts/excel-target/البركة شركات/20260907_1600/match_only_summary_البركة شركات.jsonl`

الـ50 صفاً موجودة، وكل المطابقات الثلاث عشرة compatibility-compatible، ولا توجد
إضافة للسلة لأن الوضع كان `--match-only`.

## حالة suite المشروع

تم تشغيل `pytest -q tests` في 81.34 ثانية: `21 failed, 974 passed, 19 skipped,
8 warnings, 134 subtests passed`. الفشل خارج نطاق Baraka/Excel-target، ومن أمثلته
اختبارات Streamlit التي تستدعي `st.button` داخل `st.form`، واختبارات CLI/DB
الموجودة في حالة worktree الحالية. لذلك لا يُعلن هذا التقرير أن المشروع كله
أخضر. بوابة Baraka وExcel Target المذكورة أعلاه خضراء بالكامل.
# Final verification addendum (2026-09-07, run 20260907_1752)

The latest implementation was verified after the Manual Review provenance
changes. The original command completed successfully in about 50 seconds.

Baraka results: 50 processed, 13 `matched-only`, 37 `no-results`; 8 rows have
`manual_review_required=1` and 15 target-only candidate options in total. The
candidate CSV/JSONL artifacts are under
`artifacts/excel-target/البركة شركات/20260907_1752/`.

The candidate loader and UI now discover all Excel Target candidate files,
display source/target/file/evidence, and keep Tawreed products out of Baraka
candidate options. SQLite stores `matching_source`, `matching_source_label`,
identity evidence, and the explicit decision (`auto_matched` or
`approved_match`). The editable-table approval path also preserves these fields.

Focused implementation gate: **146 passed**. Diagnostic/reproduction gate:
**24 passed**. Full repository result: **987 passed, 21 failed, 19 skipped**;
the remaining failures are out-of-scope pre-existing CLI/encoding, order-runs
migration, matching-hypothesis, exception-audit, and Run DB Streamlit tests.
