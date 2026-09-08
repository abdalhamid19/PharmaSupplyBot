# خطة كاملة لزيادة المطابقة بأمان

## المرحلة 0: بوابة baseline وإعادة الإنتاج

شغّل:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\core\excel_target tests\diagnostics\test_baraka_matching_hypotheses.py tests\diagnostics\test_baraka_solution_scorecard.py tests\test_product_matching.py tests\cli\commands\test_excel_target_e2e.py
```

لا يبدأ أي تحسين إذا فشلت بوابة safety. احفظ stdout، زمن التنفيذ، ونسخة
الـartifacts في مجلد تشغيل مؤرخ، ثم قارن أي نتيجة لاحقة بنفس input والـconfig.

آخر بوابة نجاح موثقة هي `87 passed, 8 subtests passed in 27.41s`؛ لا تُستبدل
بنتيجة `pytest -q tests` العامة لأنها تحتوي failures مستقلة عن Baraka.

## المرحلة 1: قياس التغطية

التنفيذ الحالي يتم بالأمر offline التالي:

```powershell
.\.venv\Scripts\python.exe scripts\baraka_coverage_report.py --config state\config.yaml --excel data\input\order_items\0000000000006777.xlsx --target-key "البركة شركات" --target-path "data\input\excel target\البركة شركات.xlsx" --limit 50 --prevented-items-excel data\input\prevented_items\drugprevented.xlsx --output-prefix "artifacts\excel-target\البركة شركات\20260907_coverage\baraka_coverage_البركة شركات"
```

نتيجة التشغيل: `identity_absent=29`، `identity_variant_rejected=9`،
`identity_compatible=12`، مع 4,107 صفاً في catalog و50 item في التقرير.

أنشئ تقريراً لكل item ولكل صف Baraka يفرق بين:

- native English.
- `egyptian_drugs.csv` hit.
- translation cache hit.
- Tawreed alias hit مع صف Baraka موجود.
- identity absent.
- identity موجود لكن variant مرفوض.

لا تخلط هذه الفئات في رقم واحد `no-results`.
أضف لكل صف `target_key`, `source_file`, `item_code`, `candidate_count`,
`identity_evidence_kind`, `compatibility_status`, `compatibility_rejection`،
و`match_elapsed_ms`. التقرير المنفذ يفسر replay الأخير إلى 29 نقص هوية و8
رفض خصائص، لا أن يكتفي بعدّ no-results.

## المرحلة 2: مصادر الهوية بالترتيب

الترتيب الآمن المقترح:

1. native English في Baraka.
2. exact dictionary alias.
3. exact Tawreed alias مربوط بصف Baraka، من CSV محلي فقط.
4. cached translation exact brand.
5. manual review محدد بـtarget key وrow code وsource file عند الحاجة.

لا تستخدم fuzzy brand وحده للاعتماد التلقائي.
لا تنشئ `TargetProduct` من Tawreed، ولا تنقل منه سعراً أو كمية أو orderability.
احتفظ بكل variants للعلامة قبل compatibility filter؛ الاختلاف المعروف في الشكل
أو التركيز أو العبوة رفض قطعي.

## المرحلة 3: تطبيع الأسماء والخصائص

اختبر وأضف فقط تحويلات قابلة للتدقيق:

- `MGC` إلى `MCG`.
- `FLIM` إلى `FILM` إذا كان الحقل وصفاً للشكل وليس brand.
- singular/plural form tokens.
- اختلاف المسافات والهمزات العربية.

كل تطبيع جديد يجب أن يملك test يمنع دمج علامتين مختلفتين.
اختبر أيضاً الوحدات (`1 g == 1000 mg`، لكن `1 ml != 1 mg`) وغياب الخاصية:
وجود form/strength/pack في الطلب دون دليل في المرشح ينتج manual-review/no-results.

## المرحلة 4: pre-translation

استخدم:

```powershell
.\.venv\Scripts\python.exe scripts\pre_translate_catalog.py --excel "data/input/excel target/البركة شركات.xlsx" --name-col الصنف --dry-run
```

الـdry-run الذي تم التحقق منه أعاد `4,105` أسماء فريدة، منها `4,105` في
الـcache و`286` pending، أي `3` batches بحجم 100؛ لا يرسل هذا الأمر أي طلب
شبكة.

ثم شغّل الترجمة الفعلية في بيئة مزودة بمفتاح Cohere وبعد موافقة تشغيلية منفصلة،
وراجع cache قبل replay. لا تستدع live provider داخل matcher أو fallback الخاص
بأمر الطلب. احتفظ بنسخة cache قبل العملية، وسجّل عدد الأسماء والـbatches، ولا
تعتمد أي ترجمة لم تمر بمراجعة/اختبار هوية.

## المرحلة 5: manual review

للحالات الصحيحة التي لا يمكن إثباتها آلياً:

- احفظ قراراً مرتبطاً بـ`excel_target_key`.
- احفظ `correct_store_product_id`.
- احفظ source file عند الحاجة.
- أعد تشغيل نفس scorecard.
لا تجعل قراراً قديماً بلا `excel_target_key` يفرض تطابق Baraka؛ أعد اعتماده
لنفس target و`store_product_id` أولاً.

## المرحلة 6: replay الإنتاج

نفّذ `--match-only` فقط، ثم افحص كل `matched-only`:

- identity evidence موجود.
- صف المنتج من Baraka وليس Tawreed.
- compatibility = compatible.
- لا يوجد قبول بسبب pack/form فقط.
- لا توجد مكالمة browser أو cart mutation.
- زمن الجلسة أقل من 300 ثانية لأول 50، وفهرس Tawreed/translation يُبنى مرة
  واحدة لا داخل كل item.

القياس المنفذ محفوظ في `artifacts/excel-target/البركة شركات/20260907_coverage/baraka_index_benchmark.json`:
بناء الفهرس `6741.93ms`، مطابقة 50 item في `747.14ms`، والمتوسط `14.94ms`
للعنصر، والإجمالي أقل بكثير من 300 ثانية.

## المرحلة 7: suite كاملة

شغّل بوابة Excel أولاً، ثم:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
```

أي failures خارج هذه البوابة تسجل منفصلة ولا تُخفى بتحويل الاختبارات إلى `xfail`.

## المرحلة 8: المراقبة والرجوع الآمن

بعد كل تغيير شغّل replay ثابتاً من 50 صفاً وقارن:

- عدد `matched-only`، وعدد no-results حسب السبب، لا النسبة الإجمالية فقط.
- عدم وجود match مع `compatibility_status != compatible`.
- عدم تغير نتائج English exact أو حالات INODEP السلبية.
- عدم ظهور `tawreed_catalog` إلا عندما يوجد صف Baraka عربي مرتبط فعلياً.

إذا زادت المطابقات مع اختفاء evidence أو زادت حالات form/strength mismatch، أوقف
النشر وأعد آخر artifact/commit موثق؛ لا تُعالج المشكلة بزيادة threshold أو fuzzy
fallback.

## القرار الحالي

اكتملت مراحل الإصلاح الآمن والقياس: Tawreed alias integration، التطبيع،
تقرير coverage، session benchmark، replay Excel-only، ثم الأمر الأصلي بوضع
`--match-only`. البوابة المركزة خضراء، وكل `matched-only` في آخر artifact
يحمل هوية ودليلاً متوافقاً.

المتبقي لتحسين recall فقط هو pre-translation ومراجعة aliases/قرارات manual
review بموافقة تشغيلية وبيانات Baraka مؤكدة. لا يجوز تنفيذ هذه الخطوة بإرخاء
threshold أو fuzzy fallback؛ كل alias جديد يجب أن يثبت صف Baraka وform/strength/pack
ويضيف اختبار guard قبل اعتماده.
