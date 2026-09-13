# خطة استعادة المطابقة الآمنة لكتالوج البركة 1209

> **For agentic workers:** استخدم مهارة `executing-plans` ونفّذ المهام بالترتيب، مع مراجعة نتيجة كل بوابة قبل الانتقال.

**Goal:** استعادة المطابقات الآمنة لكتالوج `البركه 1209.xlsx`، مع التمييز بين مفتاح الهدف وملف المصدر الفعلي، ومنع قبول `LIMITLESS MAN MAX` بديلاً عن `LIMITLESS MILGA MAX` وتحويل المرشح الملتبس للمراجعة اليدوية.

**Architecture:** يختار `--excel-target-path KEY=PATH` ملف الكتالوج، بينما يظل `target_key` هو اسم الهدف الظاهر ونطاق القرارات المحفوظة. يضيف التنفيذ مفتاحاً مستقلاً لـ1209 لعزل aliases والمراجعات، ثم يثبت هوية الصف العربي ويتحقق من التركيز والشكل والعبوة. وفي مسار Tawreed، يرفض حاجز الهوية المشترك الخلط بين `MILGA` و`MAN` قبل اختيار الفائز، مع إبقاء المرشح المرفوض في قائمة المراجعة اليدوية.

**Tech Stack:** Python، openpyxl، YAML، pytest، ومخرجات CSV/JSONL للمطابقة وقائمة المراجعة اليدوية.

**Spec:** طلب المستخدم الحالي وقائمة الأصناف الاثني عشر؛ خط الأساس في `artifacts/excel-target/البركة شركات/20260912_1730/match_only_summary_البركة شركات.csv`؛ والكتالوج المقصود `data/input/excel target/البركه 1209.xlsx`.

## الأدلة الحالية

- تقرير 17:30 شغّل هدف `البركة شركات`، وتُظهر قيم `source_file` للصفوف ذات المصدر `البركة شركات.xlsx`. اسم الهدف وحده لا يثبت اسم الملف الذي قُرئ.
- عند تمرير `--excel-target "البركة شركات"` مع `--excel-target-path "البركة شركات=<مسار 1209>"`، اختار المحمّل الملف `البركه 1209.xlsx` وقرأ 4,449 صفاً؛ ظل `target_key` في النتائج `البركة شركات`، وسجّل `source_file` اسم ملف 1209. إذن تجاوز المسار يعمل، لكن المفتاح المستقل غير مسجل حالياً في `state/config.yaml`.
- في ذلك التقرير، طابق `SYNOBAR-S` بالفعل، وظهر لـ`DURJOY` مرشح مراجعة رُفض لنقص دليل العبوة، بينما غابت الهوية عن ثمانية أصناف، ومنعت موافقتان قديمتان بلا row key `LEVOFLOXACIN-EVA` و`OMEGAL ULTRA` من متابعة البحث الاعتيادي. هذه نتيجة هدف `البركة شركات`، وليست نتيجة ملف 1209.
- ملف 1209 عربيّ الأسماء، فلا تظهر فيه أي من الأسماء الإنجليزية الاثني عشر حرفياً. إعادة تشغيل المطابق على هذا الملف مع تعطيل القرارات المحفوظة تعرّفت تلقائياً على `LEVOFLOXACIN-EVA` و`OMEGAL ULTRA`، ووجدت لـ`DURJOY` مرشحاً رفضه لأن عدد الأقراص غير مثبت؛ الأصناف التسعة الأخرى لم تملك دليلاً آلياً للهوية.
- توجد أسماء عربية محتملة في الصفوف المذكورة أدناه، لكن وجود الاسم القريب لا يثبت دائماً القوة أو الشكل أو حجم العبوة. `LIMITLESS MILGA MAX` تحديداً لا يملك صفاً مثبتاً له في الكتالوج؛ توجد منتجات LIMITLESS أخرى منفصلة.
- تشغيل الطلب عبر Tawreed مسار آخر: في تشغيل 11:25 أضيفت عشرة أصناف، وتخطى Levofloxacin وSynobar بسبب مقارنة السعر، وكان Pencitard مطلوباً بكمية 14 ونُفذ منه 1؛ كما طابق Limitless بديلاً خاطئاً هو `LIMITLESS MAN MAX`. لا تُحسب تلك النتائج دليلاً على أن ملف 1209 استُخدم.

## القيود العامة

- تجاوز المسار تحت المفتاح `البركة شركات` يحمّل الملف المحدد لكنه يشارك نطاق المفتاح القديم وقراراته؛ سجّل `البركه 1209` كمفتاح مستقل للاستخدام الدائم، ولا تغيّر الهدف القديم أو تخلط نتائج الكتالوجين.
- اختبر صراحةً أن تجاوز المسار تحت المفتاح القديم يغيّر `source_file` فقط ولا يغيّر `target_key`; ويجب أن تستخدم إعادة تشغيل 1209 النهائية المفتاح المستقل.
- لا تقبل صفاً عربياً بلا دليل هوية معروف أو alias معتمد ومحدد للهدف.
- يجب أن تبقى بوابات التركيز والشكل والعبوة قائمة؛ المعلومة غير الموجودة في الصف تعني مراجعة أو رفضاً، لا قبولاً تلقائياً.
- يجب أن تكون مطابقة Excel المحلية حتمية ودون استدعاء ترجمة مباشرة؛ أي ترجمة جماعية تبقى في خطوة pre-translation الصريحة.
- لا تعتمد `LIMITLESS MAN MAX` كمطابقة لـ`LIMITLESS MILGA MAX`. إذا أعاده بحث Tawreed كمرشح قريب، ارفضه آلياً واحتفظ به للمراجع اليدوية مع توضيح تعارض `MAN` و`MILGA`؛ لا تنشئ صفاً بديلاً في كتالوج Excel من قاموس Tawreed.
- افصل في التقارير بين `matched-only` واختيار المورد والسعر والكمية التي أضيفت فعلياً.
- اختبر قرارات المراجعة على قاعدة بيانات مؤقتة؛ لا تعدّل قرارات المستخدم المحفوظة أو بقية تغييرات مساحة العمل.

---

## خريطة الملفات

- `state/config.yaml`: تعريف مفتاح 1209 المستقل وظهوره في قائمة الأهداف، مع إبقاء `البركة شركات` كما هو.
- `src/core/excel_target/excel_target_matching.py`: مسار تجاوز المطابقة الاعتيادية عند وجود قرار قديم غير قابل لإعادة الربط.
- `src/cli/commands/cli_order_excel_target.py`: تشغيل Excel-target عبر CLI يجب أن يستخدم الفهارس المحلية/المخزنة فقط.
- `src/core/excel_target/excel_target_identity.py` و`src/core/excel_target/excel_target_aliases.py`: مصادر الهوية والـaliases المحددة بهدف البركة.
- `src/core/matching/product_matching_acceptance.py`: حاجز الهوية المشترك الذي يمنع قبول بديل Tawreed ذي اسم منتج متعارض.
- `src/core/manual_review/manual_review_runtime.py`: تطبيق قرارات المراجعة المحفوظة قبل المطابقة، ومنها منع سجل `auto_matched` القديم من تجاوز تعارض الهوية.
- `src/core/ordering/order_run_artifact_rows.py`: تحديد وجوب إحالة نتيجة مرفوضة للمراجعة حتى مع وجود قرار آلي قديم.
- `src/tawreed/order/tawreed_order_match.py`: تحميل قرارات التشغيل وتفعيل `manual_review_cache_context` أثناء المطابقة الفعلية.
- `src/tawreed/order/tawreed_order_summary_build.py`: تحويل نتيجة الرفض ومرشحيها إلى سجل المراجعة اليدوية.
- `src/ui/manual_review/streamlit_manual_review_page.py`: عرض سبب رفض المرشح للمراجع قبل اتخاذ القرار.
- `scripts/baraka_coverage_report.py`: إعادة تشغيل محلية للقياس دون قراءة/إعادة ربط قرارات المستخدم المحفوظة.
- `src/core/normalization/normalizer_parsing_normalize.py` وملفات تحليل خصائص المنتج في `src/core/normalization/` و`src/core/excel_target/product_attributes.py`: اختصارات الاسم والعبوة/التركيز.
- `tests/cli/commands/test_excel_target_e2e.py`: اختيار الهدف والملف في مسار CLI.
- `tests/core/excel_target/test_baraka_safe_matching.py` و`tests/core/excel_target/test_excel_target_aliases.py` و`tests/core/excel_target/test_product_attributes.py`: اختبارات الأمان والهوية والخصائص.
- `tests/core/excel_target/test_coverage.py`: سلوك تقرير التغطية المحلي دون قرارات محفوظة.
- `tests/core/excel_target/fixtures/`: سجل ذهبي صغير يربط أسماء الطلب بصفوف الكتالوج وتوقع المطابقة أو المراجعة.

## Task 1: سجّل مفتاح 1209 المستقل واختبر الفرق بين المفتاح ومسار الملف

**Files:**
- Modify: `state/config.yaml`
- Test: `tests/cli/commands/test_excel_target_e2e.py`
- Test fixture: `tests/cli/commands/fixtures/excel_target_with_target.yaml`

- [ ] أضف `البركه 1209` إلى `excel_targets` و`user_added_targets` في `state/config.yaml`، مع `name_col: الصنف` و`price_col: سعر ج` و`discount_col: شركات` و`header_row: 0`، واترك اختيار أول sheet أو سمِّ sheet الموجودة `محروس ص` صراحةً. طابق هجاء المفتاح مع اسم الملف كي يحل المسار الافتراضي إلى `data/input/excel target/البركه 1209.xlsx`. سبب المفتاح الجديد هو عزل aliases والقرارات المحفوظة واسم التقرير؛ تجاوز المسار الحالي تحت المفتاح القديم يعمل بالفعل.
- [ ] أضف fixture مصغّراً بثلاثة أعمدة وبـsheet/header مماثلين. اختبر مسارين: (أ) اختيار `البركة شركات` مع override إلى fixture باسم 1209، والتحقق أن `target_key` يظل `البركة شركات` و`source_file` يسجل اسم الملف البديل؛ (ب) اختيار `البركه 1209` دون override، والتحقق من مساره الافتراضي ومصدره. لا تعتمد الاختبارات على ملف المستخدم المحلي.
- [ ] شغّل بوابة الاختبار: `.\.venv\Scripts\python.exe -m pytest -q tests\core\excel_target\test_excel_target.py tests\cli\commands\test_excel_target_e2e.py`.

**Expected:** يمكن توجيه المفتاح القديم مؤقتاً إلى ملف بديل مع بقاء provenance صحيحاً، ويعمل المفتاح المستقل `البركه 1209` افتراضياً دون تغيير ملف `البركة شركات` أو خلط نطاقاتهما.

## Task 2: أصلح رجوع المطابقة بعد قرار محفوظ قديم

**Files:**
- Modify: `src/core/excel_target/excel_target_matching.py`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`

- [ ] أضف اختباراً يحاكي تشغيل المفتاح نفسه `البركة شركات` أولاً على ملفه القديم ثم على ملف 1209 عبر override، مع موافقة محفوظة بلا `excel_target_row_key` لمنتج لم يعد موجوداً في كتالوج 1209، ومع وجود هوية حالية صالحة لنفس عنصر الطلب. أثبت أن فشل إعادة الربط يُسجل ثم تستمر المطابقة الاعتيادية، بدلاً من إرجاع `Saved product is absent from current Excel file` وإخفاء المرشح الحالي.
- [ ] أضف اختباراً مقابلاً يثبت أن قرارات `not_matching` و`needs_correction` الصريحة تظل مانعة للمطابقة التلقائية.
- [ ] في هذا الاختبار، وجّه `src.core.manual_review.manual_review_store.DEFAULT_MANUAL_REVIEW_DB` إلى ملف مؤقت؛ لا تقرأ أو تكتب `state/manual_review_decisions.db`.
- [ ] عدّل `_scoped_manual_review`/`ExcelTargetMatcher.match` بحيث يكون فشل إعادة ربط موافقة قديمة غير مانع للبحث الحالي، مع الإبقاء على تحقق target/row key والتوافق قبل تطبيق أي موافقة محفوظة.
- [ ] شغّل: `.\.venv\Scripts\python.exe -m pytest -q tests\core\excel_target\test_baraka_safe_matching.py`.

**Expected:** عند استعمال override تحت المفتاح `البركة شركات`، لا تحجب موافقة قديمة بلا row key المطابقة بعد تبديل ملف المصدر؛ يستمر البحث ويصدر نتيجة أو مراجعة حسب أدلة 1209. موافقات الصفوف المحددة تبقى مرتبطة بالمفتاح والصف. المفتاح المستقل `البركه 1209` يعزل إعادة التشغيل الدائمة عن قرارات الهدف القديم، لكنه لا يثبت وحده هوية أي منتج أو توافق خصائصه.

## Task 3: ثبّت سجل الصفوف الاثني عشر ونتيجة كل حالة

**Files:**
- Create: `tests/core/excel_target/fixtures/baraka_1209_gold_labels.csv`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`

- [ ] أضف سجلاً لكل item code/اسم، ورقم صف المصدر، والاسم العربي الخام، والحالة المتوقعة (`auto_match`, `review`, `no_match`) وسببها. ابدأ بمراجعة هذه الصفوف المؤكدة في الملف؛ الأسماء العربية مرشحة للربط فقط إلى أن يثبت صاحب الكتالوج خصائصها:

| Item code | الاسم في الطلب | صف/اسم الكتالوج المحتمل | نقطة التحقق |
|---|---|---|---|
| 23031 | `ELBAVIT SYP 60 ML` | 353 `البافيت بالحديد 60مل شراب`؛ 354 `البافيت كالسيوم 60مل شراب` | مكوّن الحديد/الكالسيوم يترك الحالة ملتبسة |
| 64430 | `DURJOY 60 MG 3 TAB` | 2115 `ديورجوى 60 مجم اقراص` | عدد الأقراص 3 غير مذكور |
| 73151 | `PENCITARD 1200000 i.u vial` | 1229 `بنسيتارد فيال` | قوة 1,200,000 IU غير مثبتة |
| 74209 | `PROTOFIX 40MG 14 TAB` | 1073 `بروتوفكس40مجم اقراص س ج` | حجم عبوة 14 غير مذكور |
| 74659 | `ZOLADEX DEPOT 3.6 MG AM` | 2311 `زولاديكس 3.6مجم 1سرنجة` | معنى `AM` وتوافق الشكل يحتاجان توثيقاً |
| 80532 | `LOGUSGYN 10 SUPPOSITORIES` | 3725 `لوجس جين لبوس مهبلي` | عبوة 10 غير مذكورة |
| 81148 | `SYNOBAR-S SOAP 100GM` | 2796 `سينوبار اس صابونة` | الوزن 100 جم غير مذكور |
| 87486 | `CONVENTIN XR 300 MG 30 TABS` | 3546 `كونفينتين 300 اكس ار ممتد المفعول ق` | عبوة 30 غير مذكورة |
| 88189 | `LEVOFLOXACIN-EVA 500 MG 10 F.C.TABS.` | 3808 `ليفوفلوكساسين ايفا 500مجم 10اقراص` | تحقّق أن التطبيع يستخرج عبوة 10 أقراص |
| 90893 | `quadriderm cream 15g` | 3431 `كوادريدرم كريم س ج` | حجم 15 جم غير مذكور |
| 90993 | `OMEGAL ULTRA 30CAP` | 791 `اوميجال الترا 30كبسولة` | تحقّق من تطابق الاسم والعبوة |
| 92558 | `LIMITLESS MILGA MAX 30 TABS` | لا يوجد صف يثبت نسخة `MILGA MAX` في كتالوج 1209 الفعلي | تظل نتيجة كتالوج 1209 `no_match`؛ لا تفبرك صفاً. يعالج Task 5 مرشح Tawreed السابق `LIMITLESS MAN MAX`: لا يقبله آلياً ويُرسله للمراجعة اليدوية |
- [ ] لا تصنّف المرشح كـ`auto_match` اعتماداً على التشابه وحده. أبقِ ELBAVIT للمراجعة لوجود الحديد والكالسيوم كصفين؛ وابقِ pack/strength/form غير المثبت في DURJOY وPENCITARD وPROTOFIX وZOLADEX وLOGUSGYN وSYNOBAR-S وCONVENTIN وQUADRIDERM للمراجعة أو الرفض.
- [ ] سجّل LEVOFLOXACIN-EVA وOMEGAL ULTRA كحالتَي قبول فقط إذا بقي row name والعبوة متوافقين بعد إصلاح التحليل. سجّل LIMITLESS كـ`no_match` ما لم يظهر صف مستقل موثق لـ`MILGA MAX`؛ لا تستخدم `ليمتلس باور ماكس` أو`ميلجا ادفانس` كبديل.
- [ ] اكتب اختباراً يقرأ الـfixture ويقارن كل قرار بالمطابقة الفعلية على بيانات عربية مصطنعة مكافئة، حتى لا يعتمد الاختبار الآلي على ملف المستخدم المحلي غير المتعقب.

**Expected:** كل واحدة من الاثنتي عشرة لها نتيجة معللة قابلة للمراجعة، ولا يتحول نقص بيانات العبوة إلى قبول صامت.

## Task 4: أضف aliases محددة بالهدف وطبّع الاختصارات المثبتة

**Files:**
- Modify: `src/core/excel_target/excel_target_aliases.py`
- Modify: `src/core/excel_target/excel_target_identity.py`
- Modify: `src/core/excel_target/excel_target_matching.py`
- Modify: `src/cli/commands/cli_order_excel_target.py`
- Modify: `src/core/normalization/normalizer_parsing_normalize.py` وأداة تحليل الخصائص ذات الصلة
- Test: `tests/core/excel_target/test_excel_target_aliases.py`
- Test: `tests/core/excel_target/test_product_attributes.py`

- [ ] أضف مساراً لتمرير aliases معتمدة ومحددة بـ`target_key=البركه 1209` إلى فهرس الهوية، مع مصدر/مرجع صف لكل alias. لا تضع أسماء هذا الكتالوج في قاموس عام يؤثر على أهداف أخرى، ولا تتوقع أن تنطبق هذه aliases على override يظل مفتاحه `البركة شركات`. حافظ على حد alias الحالي (درجة 96 وهامش 4) وعلى تحقق التوافق بعد اكتشاف الهوية.
- [ ] أضف فقط aliases التي يثبتها سجل الصفوف أو قاموس موثوق: الاسم الإنجليزي، النص العربي المطابق للصف، والخصائص المتاحة. إذا لم تثبت خاصية لازمة، يجب أن ينتج المرشح مراجعة لا قبولاً.
- [ ] أضف اختبارات تطبيع مستقلة على الإدخالات الحرفية `ELBAVIT SYP` و`PENCITARD 1200000 i.u vial` و`LEVOFLOXACIN-EVA 500 MG 10 F.C.TABS.`؛ يجب أن تتعرف على شراب، و`1200000 IU`، وعبوة 10 أقراص مغلفة. لا تعرّف `AM` كـampoule عاماً؛ لا تضف هذا التفسير لـZOLADEX إلا إذا وثّق مرجع المنتج أنه المقصود.
- [ ] اجعل `run_excel_target_match_only_multi` يستخدم `allow_live_translation=False` افتراضياً؛ أضف اختباراً يثبت أن مسار المطابقة لا يستدعي مزوّد ترجمة. تبقى ترجمة الكتالوج خطوة منفصلة وصريحة عبر أداة pre-translation.
- [ ] أضف حواجز سلبية: اختلاف نسخة ELBAVIT (حديد/كالسيوم)، غياب قوة PENCITARD، وغياب عدد الأقراص/الوزن. لا تنشئ alias أو صف Excel-target يوحّد `LIMITLESS MAN MAX` و`LIMITLESS MILGA MAX`؛ يعالج Task 5 مرشح Tawreed السابق ومسار مراجعته.
- [ ] شغّل: `.\.venv\Scripts\python.exe -m pytest -q tests\core\excel_target\test_excel_target_aliases.py tests\core\excel_target\test_product_attributes.py tests\core\excel_target\test_baraka_safe_matching.py`.

**Expected:** يمكن توليد مرشحين للتهجئات الثنائية اللغة الموثقة، لكن المطابقة التلقائية تظل مشروطة بتوافق الجرعة والشكل والعبوة وعدم وجود التباس.

## Task 5: ارفض بديل Tawreed الملتبس وأرسله للمراجعة اليدوية

**Files:**
- Modify: `src/core/matching/product_matching_acceptance.py`
- Modify: `src/core/matching/matching_risk.py`
- Modify: `src/core/manual_review/manual_review_runtime.py`
- Modify: `src/core/ordering/order_run_artifact_rows.py`
- Modify: `src/tawreed/order/tawreed_order_summary_build.py`
- Modify: `src/ui/manual_review/streamlit_manual_review_page.py`
- Test: `tests/test_product_matching.py`
- Modify: `tests/test_latest_no_results_regressions.py`
- Test: `tests/core/manual_review/test_manual_review_runtime.py`
- Test: `tests/core/matching/test_matching_risk.py`
- Test: `tests/tawreed/matching/test_tawreed_search_logic.py`
- Test: `tests/tawreed/api/test_tawreed_api_execution_mode.py`
- Create: `tests/tawreed/order/test_limitless_manual_review.py`
- Test: `tests/ui/manual_review/test_streamlit_manual_review.py`

- [ ] وسّع الحالة الموجودة في `tests/test_latest_no_results_regressions.py` للزوج نفسه بدلاً من تكرار اختبار الرفض فقط: الطلب `LIMITLESS MILGA MAX 30 TABS` ومرشح Tawreed `LIMITLESS MAN MAX 30 TABS`. أثبت أن `explain_best_product_match` لا يختاره فائزاً، ويحتفظ بسبب واضح يحدد تعارض `MILGA` و`MAN`، مع إبقاء التشخيص والمرشح متاحين للمراجعة اليدوية.
- [ ] طبّق حاجز الهوية في مسار القبول المشترك قبل اختيار الفائز، بحيث يمنع قبول `MAN MAX` اعتماداً على الكلمات المشتركة `LIMITLESS` و`MAX`، ويعمل بالطريقة نفسها لمستهلكَي API والمتصفح. لا تغيّر سلوك بقية منتجات LIMITLESS.
- [ ] افحص مسار القرار المحفوظ قبل المطابقة العادية: قد يجبر `manual_review_match` نتيجة `auto_matched` قديمة على المنتج الخاطئ قبل وصولها إلى حاجز الهوية. اجعل التعارض المثبت بين اسم الطلب والمنتج المحفوظ يمنع هذا الإجبار الآلي، مع إبقاء السجل التاريخي دون حذف أو تعديل، ثم دع المرشح المرفوض يمر لمسار المراجعة.
- [ ] امنع سياسة aggressive من إعادة ترقية تشخيص الهوية المرفوض إلى مرشح قابل للإضافة للسلة حتى إذا كان `flagged_match_action=add-to-cart`؛ اختبر أن زوج `MILGA`/`MAN` يظل مرفوضاً وأن مرشحاً آخر لا يحمل هذا التعارض يستمر وفق السياسة الحالية.
- [ ] مرّر قرار المطابقة إلى `manual_review_required` من موضعي الاستدعاء `order_item_summary_row` و`_handle_manual_review_or_auto_save`؛ عند وجود رفض صريح بسبب تعارض الهوية، لا تسمح لسجل `auto_matched` القديم بإخفاء المراجعة حتى عندما يكون `enable_auto_match_re_review_on_fail=false`.
- [ ] أنشئ اختبار تكامل في `tests/tawreed/order/test_limitless_manual_review.py`: ازرع قاعدة قرارات مؤقتة بسجل Tawreed قديم من نوع `auto_matched` يشير إلى `LIMITLESS MAN MAX`، مع تعطيل `enable_auto_match_re_review_on_fail`. شغّل مسار تنفيذ الطلب الفعلي (API أو المتصفح) ببوابة Tawreed اختبارية، وتأكد أن التنفيذ يستخدم `preload_manual_review_decisions` و`manual_review_cache_context`، ثم مرّر طلب `LIMITLESS MILGA MAX 30 TABS` ونتيجة بحث `LIMITLESS MAN MAX 30 TABS` خلال `manual_review_match` والمطابقة العادية قبل أي محاولة إضافة للسلة؛ لا تستدعِ helper منفرداً ولا تستخدم قراراً مسبق التجهيز من نوع `no-results` لتجاوز هذا المسار. تحقق أن السجل القديم لا يجبر `MAN MAX` على أن يصبح فائزاً أو يضيفه للسلة، وأن قرار المطابقة النهائي مرفوض بسبب تعارض الهوية. مرّر هذا القرار المرفوض مع ملخص `no-results` إلى مسار artifact handling، واحفظ مرشح `MAN MAX` وسبب التعارض في ملف المراجعة ضمن مجلد تشغيل مؤقت؛ حمّله عبر `load_review_candidates` وتأكد من ظهور السبب للمراجع ومن أن الصف أُحيل فعلاً للمراجعة. أثبت أن سجل `auto_matched` المزروع لم يُحذف أو يُعدّل، وأن الصنف لم يُسجّل كـ`auto_matched` جديد. وجّه `src.core.manual_review.manual_review_store.DEFAULT_MANUAL_REVIEW_DB` و`src.tawreed.order.tawreed_order_summary_build.DEFAULT_MANUAL_REVIEW_DB` إلى قاعدة مؤقتة كي لا يقرأ الاختبار قرارات المستخدم ولا يكتب إليها.
- [ ] اعرض `rejection_reason` في صفحة المراجعة اليدوية قرب اسم `LIMITLESS MAN MAX`، وأضف اختبار UI يثبت أن عبارة تعارض `MAN`/`MILGA` ظاهرة للمراجع وليست محفوظة في JSONL فقط.
- [ ] أضف حالة مقابلة تثبت أن صفاً موثقاً باسم `LIMITLESS MILGA MAX` لا يتأثر بالحاجز، ثم شغّل: `.\.venv\Scripts\python.exe -m pytest -q tests\test_product_matching.py tests\test_latest_no_results_regressions.py tests\core\manual_review\test_manual_review_runtime.py tests\core\matching\test_matching_risk.py tests\tawreed\matching\test_tawreed_search_logic.py tests\tawreed\api\test_tawreed_api_execution_mode.py tests\tawreed\order\test_limitless_manual_review.py tests\ui\manual_review\test_streamlit_manual_review.py`.

**Expected:** لا يتحول `LIMITLESS MAN MAX` إلى مطابقة آلية أو إضافة للسلة لطلب `MILGA MAX`، ولا يخفيه سجل `auto_matched` قديم عن المراجعة؛ يظهر للمراجع اليدوي كمرشح مع سبب اختلاف الهوية قبل أن يتخذ قراره، مع بقاء السجل التاريخي محفوظاً. وتظل مطابقة `MILGA MAX` الحقيقي ممكنة عند ثبوتها.

## Task 6: أعد تشغيل المطابقة محلياً مع حفظ provenance بأمان

**Files:**
- Modify: `scripts/baraka_coverage_report.py`
- Test: `tests/core/excel_target/test_coverage.py`
- Test: `tests/cli/commands/test_excel_target_e2e.py`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`
- Output: ملف CSV/JSONL مؤقت للمقارنة، بلا تعديل لكتالوج المستخدم

- [ ] اجعل `scripts/baraka_coverage_report.py` ينشئ المطابق باستخدام `use_saved_approvals=False` حتى لا يقرأ قرارات الهدف القديم أو يعيد ربطها/يكتبها. أضف اختباراً يثبت أن matcher تقرير التغطية معطّل القرارات المحفوظة ولا يستدعي قراءة أو كتابة `ManualReviewStore`.
- [ ] في اختبار CLI داخل العملية نفسها بكتالوج fixture محفوظ في ملف مؤقت اسمه `البركه 1209.xlsx`، أنشئ `AppConfig` اختباريّاً بقيمة `database.order_runs_path` مؤقتة باستخدام `dataclasses.replace` مع إنشاء `DatabaseConfig` بديل؛ الكائنان مجمّدان ولا تعدّل الخاصية مباشرة. ووجّه الثابتين `src.core.manual_review.manual_review_store.DEFAULT_MANUAL_REVIEW_DB` و`src.cli.commands.cli_order_excel_target.DEFAULT_MANUAL_REVIEW_DB` إلى قاعدة مؤقتة. استدعِ مسار المطابقة فقط، ثم تحقق من الحقول: `matching_source=excel-target`؛ و`matching_source_label=<target_key>@<source_file>`، وقيمته هنا `البركه 1209@البركه 1209.xlsx`؛ و`storeName=excel-target:<target_key>@<source_file>`، وقيمته هنا `excel-target:البركه 1209@البركه 1209.xlsx`. لا تشغّل أمراً فرعياً يكتب إلى قاعدة قرارات المستخدم.
- [ ] شغّل تقرير التغطية على الطلب الفعلي والهدف الجديد:

```powershell
.\.venv\Scripts\python.exe scripts\baraka_coverage_report.py `
  --config state\config.yaml `
  --excel data\input\order_items\12092026.xlsx `
  --target-key "البركه 1209" `
  --target-path "data\input\excel target\البركه 1209.xlsx" `
  --limit 2000 `
  --output-prefix "$env:TEMP\baraka-1209-after"
```

- [ ] راجع صفوف الأكواد الاثني عشر في التقرير؛ يجب أن يرتبط التقرير بمفتاح `البركه 1209` وحجم كتالوجه، وأن تطابق كل نتيجة تصنيف السجل الذهبي. لا تشترط وجود `source_file` في الصفوف التي لم تنتج مرشحاً؛ تحقّق من اسم المصدر عند وجود مرشح أو منتج فقط. سجّل منفصلةً عدد المطابقات التلقائية، المرشحين للمراجعة، والرفض مع السبب.
- [ ] شغّل بوابة Excel Target وCLI: `.\.venv\Scripts\python.exe -m pytest -q tests\core\excel_target tests\cli\commands\test_excel_target_e2e.py`.
- [ ] قارن مع تشغيل `20260912_1125`: سجّل أن Levofloxacin وSynobar تم تخطيهما وقتها بسبب مقارنة السعر، وأن PENCITARD طلب 14 لكن المنفذ كان 1، وأن نتيجة LIMITLESS MAN MAX غير صحيحة ولا تُحسب كاستعادة ناجحة لمطابقة `MILGA MAX`.

**Expected:** يصبح ممكناً تمييز عدم تحميل الملف من فقدان الهوية أو فشل التوافق. تقرير التغطية يعيد المطابقة العادية دون قراءة أو تعديل قرارات المستخدم، واختبار CLI يتحقق من provenance على قواعد بيانات مؤقتة؛ لا ينفذ طلباً ولا يكتب إلى `state/manual_review_decisions.db`.
